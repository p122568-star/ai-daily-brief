import os
import sys
import datetime
import requests
from playwright.sync_api import sync_playwright
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일 로드 (스크립트 위치 기준)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# 환경변수 로드
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SONO_ID = os.getenv("SONO_ID")
SONO_PW = os.getenv("SONO_PW")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("텔레그램 토큰이 설정되지 않았습니다.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # 텔레그램 메시지 최대 4096자 제한 — 초과 시 분할 전송
    max_len = 4000
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for chunk in chunks:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"텔레그램 전송 오류: {e}")

def send_telegram_photo(photo_path, caption=""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": f},
                timeout=15
            )
    except Exception as e:
        print(f"사진 전송 오류: {e}")

def parse_with_gemini(raw_text, page_num):
    """각 페이지 텍스트를 Gemini로 파싱"""
    if not GEMINI_API_KEY:
        return raw_text[:1000]

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    아래는 소노호텔 패키지 안내 웹페이지 {page_num}번째 페이지의 텍스트 데이터입니다.
    이 데이터에서 패키지 상품들을 찾아 다음 형식으로 보기 좋게 정리해주세요:

    📦 패키지명: [패키지명]
    📍 지역: [지역명]
    📅 예약기간: [예약기간]
    📋 구성내용: [구성내용 요약]
    💰 금액: [금액]

    - 패키지가 여러 개라면 모두 나열해주세요.
    - 패키지 정보가 전혀 없으면 반드시 "패키지없음" 이라고만 답하세요.
    - 불필요한 메뉴, 버튼 텍스트, 헤더/푸터 내용은 무시하세요.

    [원본 텍스트 시작]
    {raw_text[:25000]}
    [원본 텍스트 끝]
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API 호출 중 오류 (페이지 {page_num}): {e}")
        return None

def scrape_all_pages(page):
    """모든 패키지 페이지를 순회하며 텍스트 수집 및 파싱"""
    all_results = []
    current_page = 1
    MAX_PAGES = 20  # 무한 루프 방지용 최대 페이지 수

    while current_page <= MAX_PAGES:
        url = f"https://www.sonohotelsresorts.com/reserve/package?page={current_page}"
        print(f"  >> 페이지 {current_page} 스크래핑 중... ({url})")

        page.goto(url, wait_until="networkidle")

        # 로그인 페이지로 튕긴 경우 중단
        if "member/login" in page.url:
            print(f"  [경고] 페이지 {current_page}: 세션 만료로 로그인 페이지로 리다이렉트됨. 중단.")
            break

        # 페이지 텍스트 추출
        raw_text = page.evaluate("document.body.innerText")

        # Gemini로 파싱
        parsed = parse_with_gemini(raw_text, current_page)

        # "패키지없음" 응답 or None이면 마지막 페이지로 판단
        if parsed is None or "패키지없음" in parsed.replace(" ", ""):
            print(f"  >> 페이지 {current_page}: 패키지 없음. 수집 완료.")
            break

        print(f"  [OK] 페이지 {current_page}: 패키지 발견!")
        all_results.append((current_page, parsed))

        current_page += 1
        # 서버 부하 방지를 위한 페이지간 대기
        page.wait_for_timeout(2000)

    return all_results

def main():
    if not SONO_ID or not SONO_PW:
        print("SONO_ID 또는 SONO_PW가 설정되지 않았습니다.")
        sys.exit(1)

    print(f"[{datetime.datetime.now()}] 소노호텔 패키지 전체 스크래핑 시작...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        # 1. 로그인 (최대 3회 재시도)
        MAX_LOGIN_RETRY = 3
        login_success = False

        for attempt in range(1, MAX_LOGIN_RETRY + 1):
            try:
                print(f"로그인 시도 중... ({attempt}/{MAX_LOGIN_RETRY})")
                page.goto("https://www.sonohotelsresorts.com/member/login", wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                # 입력 필드 초기화 후 입력
                page.fill("input#lginId", "")
                page.fill("input#lginPw", "")
                page.wait_for_timeout(500)
                page.type("input#lginId", SONO_ID, delay=80)
                page.type("input#lginPw", SONO_PW, delay=80)
                page.wait_for_timeout(800)

                # 로그인 버튼 클릭 (여러 셀렉터 시도)
                clicked = False
                for btn_selector in ['button.btn.xl.fill', 'button[type="submit"]', '.login-btn', '#loginBtn']:
                    try:
                        btn = page.locator(btn_selector).first
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            clicked = True
                            break
                    except Exception:
                        continue
                if not clicked:
                    page.keyboard.press("Enter")

                # 팝업/얼럿 처리
                page.wait_for_timeout(1500)
                try:
                    page.locator(".modal .btn-close, .popup .close, .alert .confirm").first.click(timeout=2000)
                except Exception:
                    pass

                # 로그인 완료 대기
                page.wait_for_url(
                    lambda url: "member/login" not in url,
                    timeout=20000
                )
                login_success = True
                print(f"로그인 성공! (시도 {attempt}회)")
                break

            except Exception as e:
                print(f"  [재시도] {attempt}회 로그인 실패: {e}")
                if attempt < MAX_LOGIN_RETRY:
                    wait_sec = attempt * 5
                    print(f"  {wait_sec}초 후 재시도...")
                    page.wait_for_timeout(wait_sec * 1000)

        if not login_success:
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.png")
            try:
                page.screenshot(path=screenshot_path)
                msg = f"소노호텔 로그인 {MAX_LOGIN_RETRY}회 모두 실패했습니다.\n(아이디/비밀번호 또는 네트워크 오류)"
                print(msg)
                send_telegram_photo(screenshot_path, f"🚨 소노호텔 스크래핑 오류\n{msg}\n현재 화면 상태입니다.")
            except Exception:
                msg = f"소노호텔 로그인 {MAX_LOGIN_RETRY}회 모두 실패했습니다."
                send_telegram(f"🚨 소노호텔 스크래핑 오류\n{msg}")
            browser.close()
            sys.exit(1)

        page.wait_for_timeout(2000)
        print("로그인 완료!")

        # 2. 전체 페이지 스크래핑
        print("전체 패키지 페이지 순회 시작...")
        all_results = scrape_all_pages(page)
        browser.close()

    # 3. 결과 텔레그램 전송
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_pages = len(all_results)

    if total_pages == 0:
        send_telegram(f"🏨 <b>소노호텔 패키지 정보 ({current_time})</b>\n\n현재 등록된 패키지 상품이 없습니다.")
    else:
        # 헤더 메시지 먼저 전송
        header = f"🏨 <b>소노호텔 패키지 전체 목록 ({current_time})</b>\n총 <b>{total_pages}페이지</b> 수집 완료\n{'─'*30}"
        send_telegram(header)

        # 페이지별로 결과 전송
        for page_num, parsed in all_results:
            page_msg = f"📄 <b>[{page_num}페이지]</b>\n\n{parsed}"
            send_telegram(page_msg)

    print(f"전체 스크래핑 완료! ({total_pages}페이지 수집) 텔레그램 전송 완료!")

if __name__ == "__main__":
    main()

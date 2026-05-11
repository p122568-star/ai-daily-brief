import yfinance as yf
import feedparser
import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import webbrowser
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

import sys

# .env 파일 로드
load_dotenv()

# 로그 설정
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_daily_brief.log")

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

log("AI Daily Briefing 시작")

# 설정 - 사용자의 요청에 따라 S&P 500과 나스닥만 유지
STOCKS = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ"
}

NEWS_FEEDS = [
    "https://news.google.com/rss/search?q=%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5+%EC%A3%BC%EC%8B%9D&hl=ko&gl=KR&ceid=KR:ko", # 인공지능 주식
    "https://news.google.com/rss/search?q=AI+%EA%B8%B0%EC%88%A0+%ED%8A%B8%EB%A0%8C%EB%93%9C&hl=ko&gl=KR&ceid=KR:ko", # AI 기술 트렌드
    "https://news.google.com/rss/search?q=NVIDIA+Microsoft+AI+%EC%86%8C%EC%8B%9D&hl=ko&gl=KR&ceid=KR:ko" # NVIDIA Microsoft AI 소식
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Intelligence Briefing</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #020617;
            --card-bg: rgba(30, 41, 59, 0.4);
            --accent-cyan: #06b6d4;
            --accent-purple: #8b5cf6;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --up-color: #10b981;
            --down-color: #ef4444;
        }}

        body {{
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 0;
            background-image: radial-gradient(circle at 10% 10%, #1e1b4b 0%, transparent 40%),
                              radial-gradient(circle at 90% 90%, #312e81 0%, transparent 40%);
            min-height: 100vh;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 60px 20px;
        }}

        header {{
            text-align: left;
            margin-bottom: 80px;
            border-left: 5px solid var(--accent-cyan);
            padding-left: 30px;
        }}

        h1 {{
            font-size: 4rem;
            margin: 0;
            font-weight: 800;
            letter-spacing: -2px;
            line-height: 1;
        }}

        .date {{
            color: var(--accent-purple);
            font-size: 1.5rem;
            font-weight: 500;
            margin-top: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .section-title {{
            font-size: 2.2rem;
            margin: 60px 0 30px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 20px;
        }}

        .section-title::after {{
            content: "";
            flex: 1;
            height: 1px;
            background: linear-gradient(to right, var(--text-dim), transparent);
            opacity: 0.2;
        }}

        .stock-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 40px;
        }}

        .stock-card {{
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 32px;
            padding: 40px;
        }}

        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }}

        .stock-info {{
            display: flex;
            flex-direction: column;
        }}

        .stock-name {{
            font-size: 1.2rem;
            color: var(--text-dim);
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .stock-price {{
            font-size: 3.8rem;
            font-weight: 700;
            margin: 5px 0;
            letter-spacing: -1px;
        }}

        .stock-change {{
            font-size: 1.3rem;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 12px;
            display: inline-block;
            width: fit-content;
        }}

        .change-up {{ background: rgba(16, 185, 129, 0.1); color: var(--up-color); }}
        .change-down {{ background: rgba(239, 68, 68, 0.1); color: var(--down-color); }}

        .toggle-container {{
            display: flex;
            background: rgba(255,255,255,0.05);
            padding: 6px;
            border-radius: 18px;
            gap: 6px;
            border: 1px solid rgba(255,255,255,0.1);
        }}

        .toggle-btn {{
            background: transparent;
            border: none;
            color: var(--text-dim);
            padding: 10px 24px;
            border-radius: 12px;
            cursor: pointer;
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 0.9rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .toggle-btn.active {{
            background: var(--accent-cyan);
            color: white;
            box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
        }}

        .chart-container {{
            margin-top: 30px;
            width: 100%;
            height: 400px;
            border-radius: 24px;
            overflow: hidden;
            background: rgba(0,0,0,0.2);
        }}

        .chart-img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}

        .news-item {{
            background: rgba(255,255,255,0.02);
            border-radius: 28px;
            padding: 35px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.05);
            text-decoration: none;
            color: inherit;
            display: block;
            transition: all 0.3s ease;
        }}

        .news-item:hover {{
            background: rgba(255,255,255,0.05);
            border-color: var(--accent-cyan);
            transform: translateY(-5px);
        }}

        .news-title {{
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 15px;
            line-height: 1.4;
        }}

        .news-meta {{
            color: var(--text-dim);
            font-size: 1rem;
            display: flex;
            gap: 25px;
            font-weight: 500;
        }}

        @media (max-width: 768px) {{
            .stock-header {{ flex-direction: column; align-items: flex-start; gap: 20px; }}
            .stock-price {{ font-size: 2.8rem; }}
            h1 {{ font-size: 3rem; }}
        }}

        .footer {{
            text-align: center;
            margin-top: 120px;
            padding-bottom: 60px;
            color: var(--text-dim);
            font-size: 1rem;
            font-weight: 500;
        }}
    </style>
    <script>
        function toggleChart(symbol, type) {{
            const card = document.getElementById('card-' + symbol);
            const chart1m = document.getElementById('chart-1m-' + symbol);
            const chart1y = document.getElementById('chart-1y-' + symbol);
            const btns = card.querySelectorAll('.toggle-btn');
            
            if (type === '1m') {{
                chart1m.style.display = 'block';
                chart1y.style.display = 'none';
                btns[0].classList.add('active');
                btns[1].classList.remove('active');
            }} else {{
                chart1m.style.display = 'none';
                chart1y.style.display = 'block';
                btns[0].classList.remove('active');
                btns[1].classList.add('active');
            }}
        }}
    </script>
</head>
<body>
    <div class="container">
        <header>
            <h1>MARKET<br>INTELLIGENCE</h1>
            <div class="date">{today_str}</div>
        </header>

        <div class="section-title">Major Indices</div>
        <div class="stock-grid">
            {stock_html}
        </div>

        <div class="section-title">AI Tech News</div>
        <div class="news-list">
            {news_html}
        </div>

        <div class="footer">
            Generated by Antigravity OS | Powered by Yahoo Finance & Google News
        </div>
    </div>
</body>
</html>
"""

def create_sparkline(history, period="1mo"):
    # 차트 생성 로직
    plt.figure(figsize=(8, 4), dpi=100)
    plt.style.use('dark_background')
    
    # 데이터 준비
    prices = history['Close']
    dates = history.index
    
    # 선 그래프 그리기
    plt.plot(dates, prices, color='#06b6d4', linewidth=3)
    plt.fill_between(dates, prices, min(prices)*0.98, color='#06b6d4', alpha=0.1)
    
    # 축 설정 및 날짜 표시
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    plt.gca().spines['bottom'].set_color('#475569')
    
    plt.yticks(color='#f1f5f9', fontsize=10) # 폰트 크기 키움
    plt.xticks(color='#f1f5f9', fontsize=10)
    
    # 날짜 포맷팅
    import matplotlib.dates as mdates
    if period == "1mo":
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
    else: # 1y (월별)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    plt.grid(axis='y', color='#1e293b', linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    # 결과를 base64로 변환
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return img_str

def get_stock_data():
    stock_list = []
    log("시장 데이터 및 멀티 기간 차트 생성 중...")
    for symbol, name in STOCKS.items():
        try:
            ticker = yf.Ticker(symbol)
            
            # 1. 일별 (최근 1개월)
            hist_1m = ticker.history(period="1mo")
            current = hist_1m['Close'].iloc[-1]
            prev = hist_1m['Close'].iloc[-2]
            
            # 2. 월별 (최근 1년)
            hist_1y = ticker.history(period="1y")
            
            change = current - prev
            pct_change = (change / prev) * 100
            
            cls = "change-up" if change >= 0 else "change-down"
            sign = "+" if change >= 0 else ""
            
            # 차트 이미지 생성 (두 종류)
            img_1m = create_sparkline(hist_1m, "1mo")
            img_1y = create_sparkline(hist_1y, "1y")
            
            card = f"""
            <div class="stock-card" id="card-{symbol.replace('^', '')}">
                <div class="stock-header">
                    <div class="stock-info">
                        <div class="stock-name">{name}</div>
                        <div class="stock-price">${current:,.2f}</div>
                        <div class="stock-change {cls}">{sign}{change:,.2f} ({sign}{pct_change:.2f}%)</div>
                    </div>
                    <div class="toggle-container">
                        <button class="toggle-btn active" onclick="toggleChart('{symbol.replace('^', '')}', '1m')">일별</button>
                        <button class="toggle-btn" onclick="toggleChart('{symbol.replace('^', '')}', '1y')">월별</button>
                    </div>
                </div>
                <div class="chart-container" id="chart-1m-{symbol.replace('^', '')}">
                    <img src="data:image/png;base64,{img_1m}" class="chart-img">
                </div>
                <div class="chart-container" id="chart-1y-{symbol.replace('^', '')}" style="display:none;">
                    <img src="data:image/png;base64,{img_1y}" class="chart-img">
                </div>
            </div>
            """
            stock_list.append(card)
        except Exception as e:
            log(f"Error fetching {symbol}: {e}")
    return "".join(stock_list)

def contains_korean(text):
    import re
    return bool(re.search('[가-힣]', text))

def get_news_data():
    news_list = []
    seen_titles = set()
    log("뉴스 데이터 수집 및 한국어 기사 필터링 중...")
    for feed_url in NEWS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if entry.title in seen_titles: continue
            
            # 한국어가 포함되지 않은 기사(영어 기사 등) 제외
            if not contains_korean(entry.title):
                continue
                
            seen_titles.add(entry.title)
            
            parts = entry.title.rsplit(" - ", 1)
            title = parts[0]
            source = parts[1] if len(parts) > 1 else "Tech News"
            
            card = f"""
            <a href="{entry.link}" target="_blank" class="news-item">
                <div class="news-title">{title}</div>
                <div class="news-meta">
                    <span>{source}</span>
                    <span>{entry.published}</span>
                </div>
            </a>
            """
            news_list.append(card)
            if len(news_list) >= 10: break # 최대 10개
    return "".join(news_list)

def send_email(html_content):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")
    
    if not all([sender, password, receiver]):
        return

    log("이메일 전송 중...")
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = f"[Market Briefing] {datetime.datetime.now().strftime('%Y-%m-%d')} Report"
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        log("이메일 전송 완료!")
    except Exception as e:
        log(f"이메일 전송 실패: {e}")

def send_telegram(html_path, stock_summary):
    token = os.getenv("TELEGRAM_BOT_TOKEN").strip() if os.getenv("TELEGRAM_BOT_TOKEN") else None
    chat_id = os.getenv("TELEGRAM_CHAT_ID").strip() if os.getenv("TELEGRAM_CHAT_ID") else None
    
    if not token or not chat_id:
        log(f"텔레그램 설정이 누락되었습니다. GitHub Secrets 설정을 확인해주세요. (Token: {token is not None}, ChatID: {chat_id is not None})")
        sys.exit(1)

    log(f"텔레그램 전송 중... (Token 길이: {len(token)})")
    # 보안을 위해 토큰 앞부분만 살짝 출력
    log(f"토큰 시작부분 확인: {token[:10]}...")
    
    # 1. 텍스트 요약 전송
    text = f"📢 [AI Daily Briefing] {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
    text += stock_summary
    
    try:
        import requests
        # 메시지 전송
        r1 = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                          data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
        log(f"메시지 전송 결과: {r1.status_code}, {r1.text}")
        
        # HTML 파일 전송
        with open(html_path, "rb") as f:
            r2 = requests.post(f"https://api.telegram.org/bot{token}/sendDocument", 
                              data={"chat_id": chat_id}, 
                              files={"document": f})
            log(f"파일 전송 결과: {r2.status_code}, {r2.text}")
            
        if r1.ok and r2.ok:
            log("텔레그램 전송 완료!")
        else:
            log("텔레그램 전송 중 오류 발생 (위 로그 확인)")
    except Exception as e:
        log(f"텔레그램 전송 중 예외 발생: {e}")
        # GitHub Actions에서 실패로 표시되도록 종료 코드 1 반환
        sys.exit(1)

def main():
    today = datetime.datetime.now()
    today_str = today.strftime("%B %d, %Y")
    
    stock_html = get_stock_data()
    news_html = get_news_data()
    
    # 텔레그램용 요약 텍스트 생성
    stock_summary = ""
    for symbol, name in STOCKS.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = current - prev
            pct = (change / prev) * 100
            sign = "🔺" if change >= 0 else "🔻"
            stock_summary += f"{sign} <b>{name}</b>: ${current:,.2f} ({change:+,.2f}, {pct:+.2f}%)\n"
        except: pass

    final_html = HTML_TEMPLATE.format(
        today_str=today_str,
        stock_html=stock_html,
        news_html=news_html
    )
    
    output_path = os.path.abspath("ai_daily_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)
    
    log(f"보고서 생성 완료: {output_path}")
    
    # 알림 발송
    send_email(final_html)
    send_telegram(output_path, stock_summary)
    
    # 브라우저 열기 (CI 환경이 아닐 때만)
    if not os.getenv("GITHUB_ACTIONS"):
        webbrowser.open(f"file://{output_path}")

if __name__ == "__main__":
    main()

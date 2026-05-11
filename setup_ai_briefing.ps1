# AI Daily Briefing 자동 실행 설정 스크립트
$taskName = "AIDailyBriefing"
$scriptPath = "$PSScriptRoot\ai_daily_brief.py"
$pythonPath = "C:\Users\p1225\AppData\Local\Microsoft\WindowsApps\python.exe"
$workingDir = $PSScriptRoot

if (-Not (Test-Path $pythonPath)) {
    $pythonPath = (Get-Command python).Source
}

# 기존 작업이 있다면 삭제
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# 트리거 생성 (매일 오전 8시 실행)
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00am

# 액션 생성
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory $workingDir

# 사용자 권한 설정 (로그온 시 실행)
$principal = New-ScheduledTaskPrincipal -UserId (Get-CimInstance Win32_ComputerSystem | Select-Object -ExpandProperty UserName) -LogonType Interactive

# 작업 설정 (배터리 모드에서도 실행, 놓친 작업 즉시 실행)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 작업 등록
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Principal $principal -Settings $settings -Description "매일 오전 8시 AI 뉴스 브리핑 발송"

Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "AI Daily Briefing 작업 스케줄러 등록 완료!" -ForegroundColor Green
Write-Host "설정 시간: 매일 오전 8:00" -ForegroundColor Yellow
Write-Host "작업 이름: $taskName" -ForegroundColor Yellow
Write-Host "--------------------------------------------------" -ForegroundColor Cyan

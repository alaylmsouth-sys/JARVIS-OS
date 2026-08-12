@echo off
REM JARVIS OS 간편 실행기 — 최초 실행 시 필요한 환경을 자동으로 준비합니다.
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set PYTHON=py -3
) else (
  set PYTHON=python
)

if not exist .venv (
  echo [1/3] 전용 실행 환경을 만드는 중입니다...
  %PYTHON% -m venv .venv
  if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat
echo [2/3] 필요한 라이브러리를 확인하는 중입니다...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] JARVIS OS를 시작합니다.
echo       브라우저에서 http://127.0.0.1:8000 을 여세요.
echo       종료하려면 이 창에서 Ctrl+C를 누르세요.
start "" http://127.0.0.1:8000
python -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000
goto :eof

:error
echo 실행 준비에 실패했습니다. Python 3.10 이상이 설치되어 있는지 확인하세요.
pause
exit /b 1

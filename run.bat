@echo off
cd /d %~dp0
python -c "import uvicorn, fastapi" >nul 2>&1 || python -m pip install -q -r requirements.txt
python -m uvicorn dashboard.main:app --reload

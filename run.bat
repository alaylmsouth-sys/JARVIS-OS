@echo off
cd /d %~dp0
python -m uvicorn dashboard.main:app --reload

#!/bin/bash
# Codespace 재생성 후 복구: bash restore.sh
sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg fonts-noto-cjk
pip install -q -r requirements.txt --user 2>/dev/null || pip install -q -r requirements.txt
if [ ! -f .env ]; then
  printf "GEMINI_API_KEY=\nYT_CLIENT_ID=\nYT_CLIENT_SECRET=\n" > .env
  echo "⚠ .env를 새로 만들었습니다 — 파일을 열어 API 키를 다시 입력하세요!"
else
  echo "✅ .env 존재"
fi
echo "✅ 복구 완료. 서버: python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8000"

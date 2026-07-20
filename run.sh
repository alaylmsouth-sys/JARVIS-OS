#!/bin/bash
cd "$(dirname "$0")"

# 재빌드 등으로 패키지가 사라진 경우 자동 재설치
if ! python3 -c "import uvicorn, fastapi" >/dev/null 2>&1; then
  echo "📦 필요한 패키지가 없어 설치합니다..."
  python3 -m pip install -q -r requirements.txt
fi

python3 -m uvicorn dashboard.main:app --reload

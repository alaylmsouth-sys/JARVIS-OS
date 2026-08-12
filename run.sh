#!/usr/bin/env bash
# JARVIS OS 간편 실행기 — 최초 실행 시 필요한 환경을 자동으로 준비합니다.
set -euo pipefail

cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.10 이상이 필요합니다. 설치 후 다시 실행하세요."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "[1/3] 전용 실행 환경을 만드는 중입니다…"
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/3] 필요한 라이브러리를 확인하는 중입니다…"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo "[3/3] JARVIS OS를 시작합니다. 브라우저에서 아래 주소를 여세요."
echo "       http://127.0.0.1:8000"
echo "종료하려면 이 창에서 Ctrl+C를 누르세요."
exec python -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000

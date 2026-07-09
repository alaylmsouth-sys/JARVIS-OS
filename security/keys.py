"""security/keys.py — API 키 관리.

프로젝트 루트의 .env 파일에서 키를 읽는다. 원칙:
  - 키는 절대 코드나 memory/ JSON에 넣지 않는다 (.env는 .gitignore 대상)
  - 키가 없으면 명확한 한국어 안내를 준다
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def load_env() -> None:
    """단순 .env 파서. 이미 설정된 OS 환경변수를 우선한다."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def get_key(env_key: str) -> str | None:
    load_env()
    return os.environ.get(env_key) or None


def has_key(env_key: str) -> bool:
    return get_key(env_key) is not None

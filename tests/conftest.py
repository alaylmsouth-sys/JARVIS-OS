"""JARVIS-OS 자동 테스트를 위한 공통 초기화."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.bootstrap import ensure_memory


ensure_memory()

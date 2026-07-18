"""brain/bootstrap.py — memory 초기화 (11단계 = t29).

★★ 원칙 ★★
  - memory/*.json은 개인 데이터 → git에 올리지 않는다 (.gitignore).
  - 대신 초기 템플릿(memory/templates/)을 저장소에 두고,
    실행 시 "없는 파일만" 템플릿에서 생성한다.
  - 이미 있는 파일은 절대 덮어쓰지 않는다 (내 데이터 보호).

사용:
  대시보드 시작 시 자동 실행. 수동 실행: python3 -m brain.bootstrap
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "memory"
TEMPLATES = MEMORY / "templates"


def ensure_memory() -> list[str]:
    """템플릿에 있는데 memory/에 없는 파일을 생성. 생성된 파일명 목록 반환."""
    if not TEMPLATES.exists():
        return []
    MEMORY.mkdir(exist_ok=True)
    created: list[str] = []
    for tpl in sorted(TEMPLATES.glob("*.json")):
        dst = MEMORY / tpl.name
        if dst.exists():          # 이미 있으면 절대 건드리지 않는다
            continue
        shutil.copyfile(tpl, dst)
        created.append(tpl.name)
    return created


def main() -> None:
    created = ensure_memory()
    if created:
        print(f"✅ memory 초기화: {len(created)}개 파일 생성 — {', '.join(created)}")
    else:
        print("✅ memory 이상 없음 (모든 파일 존재)")


if __name__ == "__main__":
    sys.exit(main())

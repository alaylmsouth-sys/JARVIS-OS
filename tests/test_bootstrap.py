"""memory 분리(11단계) 테스트. 실행: python tests/test_bootstrap.py"""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from brain.bootstrap import ensure_memory, MEMORY, TEMPLATES


def main():
    # 1. 모든 코드가 참조하는 memory 파일에 템플릿이 존재하는가
    import re
    referenced = set()
    for py in ROOT.rglob("*.py"):
        if "output" in str(py) or "test_" in py.name:
            continue
        for m in re.findall(r'memory["\'\s/]+["\']?([a-z_]+\.json)',
                            py.read_text(encoding="utf-8")):
            referenced.add(m)
    referenced.discard("youtube_token.json")   # 열쇠 — 템플릿 대상 아님
    missing = [f for f in referenced if not (TEMPLATES / f).exists()]
    assert not missing, f"템플릿 누락: {missing}"

    # 2. 없는 파일만 생성 + 기존 파일은 절대 덮어쓰지 않음
    probe = MEMORY / "finance.json"
    backup = probe.read_text(encoding="utf-8")
    try:
        probe.unlink()                              # 하나 지우고
        marker = MEMORY / "scoreboard.json"         # 하나는 내용 표시해두고
        marker_backup = marker.read_text(encoding="utf-8")
        marker.write_text('{"내데이터": true}', encoding="utf-8")

        created = ensure_memory()
        assert "finance.json" in created, f"삭제된 파일 미생성: {created}"
        assert json.loads(probe.read_text(encoding="utf-8")) == {"entries": []}
        assert "내데이터" in marker.read_text(encoding="utf-8"), "기존 파일을 덮어씀!!"

        # 3. 두 번째 실행 → 생성 0건 (멱등성)
        assert ensure_memory() == [], "이미 있는데 또 생성함"
    finally:
        probe.write_text(backup, encoding="utf-8")
        marker.write_text(marker_backup, encoding="utf-8")

    # 4. 템플릿에 개인 데이터가 비어 있는가 (실수 방지 가드)
    for name, key in [("finance.json", "entries"), ("portfolio.json", "holdings"),
                      ("ai_usage.json", "calls")]:
        d = json.loads((TEMPLATES / name).read_text(encoding="utf-8"))
        assert d.get(key) == [], f"템플릿 {name}에 데이터가 들어있음: {d.get(key)[:1]}"

    print("✅ memory 분리 테스트 4/4 통과")


if __name__ == "__main__":
    main()

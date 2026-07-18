"""AI 관리센터(12단계) + 시스템센터(13단계) 테스트. 실행: python tests/test_centers.py"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

USAGE = ROOT / "memory" / "ai_usage.json"
MEMORY = ROOT / "memory"


def main():
    backup = USAGE.read_text(encoding="utf-8")
    try:
        # ── AI 관리센터 ──
        # 합성 사용 로그 주입: script 역할의 gemini 모델 2회 (실호출 1, dry 1)
        from agents.manager import status, PROVIDER_KEYS
        table = json.loads((MEMORY / "routing_table.json").read_text(encoding="utf-8"))
        r0 = table["routes"]["script"]
        json.dump({"calls": [
            {"time": "2026-07-17T10:00:00", "task": "script", "provider": r0["provider"],
             "model": r0["model"], "input_tokens": 100, "output_tokens": 200,
             "cost_krw": 12.0, "dry_run": False},
            {"time": "2026-07-17T11:00:00", "task": "script", "provider": r0["provider"],
             "model": r0["model"], "input_tokens": 10, "output_tokens": 20,
             "cost_krw": None, "dry_run": True},
        ]}, open(USAGE, "w"), ensure_ascii=False)

        s = status()
        row = next(r for r in s["routes"] if r["task"] == "script")
        assert row["calls"] == 2 and row["real_calls"] == 1, row
        assert row["tokens"] == 330, row["tokens"]
        assert row["cost_krw"] == 12 and row["unpriced"] == 1
        assert row["last_call"] == "2026-07-17T11:00:00"
        # 이 환경엔 키가 없으므로 key_ok=False + 경고 존재해야 함 (정직성)
        if not row["key_ok"]:
            assert any("미설정" in w for w in s["warnings"]), s["warnings"]
        assert all(t in PROVIDER_KEYS or t is None
                   for t in {r["provider"] for r in s["routes"]} if t), "미지 provider"

        # ── 시스템센터 ──
        from security.health import run_checks, OK, WARN, FAIL
        checks = run_checks()
        names = {c["name"] for c in checks}
        for need in ("Python", "memory 무결성", "백업 (JARVIS-DATA)", "유튜브 인증"):
            assert need in names, f"점검 누락: {need}"
        assert all(c["level"] in (OK, WARN, FAIL) for c in checks)
        integ = next(c for c in checks if c["name"] == "memory 무결성")
        assert integ["level"] == OK, integ

        # 손상된 JSON을 심으면 무결성 점검이 잡아내는가
        bad = MEMORY / "zz_broken_test.json"
        bad.write_text("{망가진", encoding="utf-8")
        try:
            integ2 = next(c for c in run_checks() if c["name"] == "memory 무결성")
            assert integ2["level"] == FAIL and "zz_broken_test.json" in integ2["detail"]
        finally:
            bad.unlink()

        print("✅ 관리/시스템센터 테스트 6/6 통과")
    finally:
        USAGE.write_text(backup, encoding="utf-8")


if __name__ == "__main__":
    main()

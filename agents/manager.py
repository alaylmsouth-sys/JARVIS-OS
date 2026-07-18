"""agents/manager.py — AI 관리센터 (12단계 = t33).

역할별 AI 배정 현황, 키 설정 여부, 사용량/비용, 점검 경고를 한눈에.

★★ 원칙 ★★
  - 사실만 표시: 비용 미산정이면 "미산정", 키 없으면 "키 없음".
  - 여기서는 아무 API도 호출하지 않는다 (파일 읽기만).

사용:  python3 -m agents.manager
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from security.keys import has_key  # noqa: E402

MEMORY = ROOT / "memory"

# provider → 필요한 환경변수
PROVIDER_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def _load(name: str) -> dict:
    return json.loads((MEMORY / name).read_text(encoding="utf-8"))


def status() -> dict:
    """역할별 AI 현황 + 경고 목록. 대시보드 표시용."""
    table = _load("routing_table.json")
    usage = _load("ai_usage.json")["calls"]

    # provider+model 단위 사용량 집계
    agg: dict[tuple, dict] = {}
    for c in usage:
        k = (c.get("provider"), c.get("model"))
        a = agg.setdefault(k, {"calls": 0, "real": 0, "in_tok": 0, "out_tok": 0,
                               "cost_krw": 0.0, "unpriced": 0, "last": None})
        a["calls"] += 1
        if not c.get("dry_run"):
            a["real"] += 1
        a["in_tok"] += c.get("input_tokens") or 0
        a["out_tok"] += c.get("output_tokens") or 0
        if c.get("cost_krw") is not None:
            a["cost_krw"] += c["cost_krw"]
        else:
            a["unpriced"] += 1
        a["last"] = c.get("time")   # calls는 시간순 append — 마지막 값이 최신

    rows, warnings = [], []
    for task, r in table.get("routes", {}).items():
        provider, model = r.get("provider"), r.get("model")
        env_key = PROVIDER_KEYS.get(provider)
        key_ok = has_key(env_key) if env_key else None
        u = agg.get((provider, model), {})
        rows.append({
            "task": task, "description": r.get("description", ""),
            "provider": provider, "model": model,
            "key_ok": key_ok,                       # True/False/None(알 수 없는 provider)
            "fallback": r.get("fallback"),
            "calls": u.get("calls", 0), "real_calls": u.get("real", 0),
            "tokens": (u.get("in_tok", 0) + u.get("out_tok", 0)) or 0,
            "cost_krw": round(u["cost_krw"]) if u.get("cost_krw") else None,
            "unpriced": u.get("unpriced", 0),
            "last_call": u.get("last"),
        })
        # 경고 수집 (사실 기반)
        if key_ok is False:
            warnings.append(f"'{task}' ({provider}): 환경변수 {env_key} 미설정 — 실호출 불가")
        if env_key is None and provider:
            warnings.append(f"'{task}': 알 수 없는 provider '{provider}' — 키 확인 불가")
        if not r.get("pricing"):
            warnings.append(f"'{task}' ({model}): 가격 미입력 — 비용이 '미산정'으로 기록됨")
        if not r.get("fallback"):
            warnings.append(f"'{task}': fallback 없음 — 해당 AI 장애 시 대기")

    return {"note": table.get("note", ""), "pricing_note": table.get("pricing_note", ""),
            "routes": rows, "warnings": warnings}


def main() -> None:
    print(json.dumps(status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

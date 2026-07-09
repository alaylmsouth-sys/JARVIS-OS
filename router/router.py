"""router/router.py — AI Router.

역할:
  1. 작업 유형(task) → routing_table.json 규칙에 따라 담당 AI 선택
  2. 호출 실행 (agents/ 어댑터 사용)
  3. 모든 호출을 memory/ai_usage.json 에 기록 (토큰, 비용) → 재무센터 데이터
  4. 첫 실제 호출 성공 시 프로젝트 작업 t7을 자동 완료 처리 (AI PM 연동)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents import writer  # noqa: E402
from brain import project_manager as pm  # noqa: E402

MEMORY = ROOT / "memory"
TABLE_FILE = MEMORY / "routing_table.json"
USAGE_FILE = MEMORY / "ai_usage.json"


def load_table() -> dict:
    with open(TABLE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _load_usage() -> dict:
    if not USAGE_FILE.exists():
        return {"calls": []}
    with open(USAGE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _estimate_cost(pricing: dict, in_tok: int, out_tok: int, usd_to_krw: float):
    """가격이 설정된 경우에만 비용 계산. 아니면 None(미산정)."""
    pi, po = pricing.get("input"), pricing.get("output")
    if pi is None or po is None:
        return None, None
    usd = in_tok / 1_000_000 * pi + out_tok / 1_000_000 * po
    return round(usd, 6), round(usd * usd_to_krw, 2)


def route(task: str, prompt: str, dry_run: bool = False) -> dict:
    table = load_table()
    if task not in table["routes"]:
        raise ValueError(f"등록되지 않은 작업 유형: {task} "
                         f"(가능: {', '.join(table['routes'])})")
    rule = table["routes"][task]
    provider = rule["provider"]
    pconf = table["providers"][provider]

    result = writer.generate(
        provider=provider,
        model=rule["model"],
        system=rule.get("system", ""),
        prompt=prompt,
        env_key=pconf["env_key"],
        dry_run=dry_run,
    )

    usd, krw = _estimate_cost(pconf.get("pricing_usd_per_1m", {}),
                              result["input_tokens"], result["output_tokens"],
                              table.get("usd_to_krw", 1400))
    record = {
        "time": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "task": task,
        "provider": provider,
        "model": result["model"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cost_usd": usd,
        "cost_krw": krw,
        "dry_run": dry_run,
    }
    usage = _load_usage()
    usage["calls"].append(record)
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(usage, f, ensure_ascii=False, indent=2)

    # 첫 실제 대본 생성 성공 → AI PM에 t7 완료 보고
    if not dry_run and task == "script":
        state = pm.load_state()
        for phase in state["phases"]:
            for t in phase["tasks"]:
                if t["id"] == "t7" and not t["done"]:
                    t["done"] = True
                    pm.save_state(state)

    return {"result": result, "usage": record}


def usage_summary() -> dict:
    """대시보드/재무센터용 요약."""
    usage = _load_usage()
    calls = usage["calls"]
    real = [c for c in calls if not c.get("dry_run")]
    total_krw = sum(c["cost_krw"] for c in real if c.get("cost_krw") is not None)
    unpriced = sum(1 for c in real if c.get("cost_krw") is None)
    return {
        "total_calls": len(calls),
        "real_calls": len(real),
        "total_cost_krw": round(total_krw, 2),
        "unpriced_calls": unpriced,
        "recent": list(reversed(calls[-10:])),
    }

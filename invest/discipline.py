"""invest/discipline.py — 매매 규율 시스템 (체크리스트 + 매매일지 + 복기 통계).

철학:
  - AI가 확률을 지어내지 않는다. 통계는 오직 사용자 본인의 매매 기록에서 나온다.
  - 매수 기록에는 계획(손절/목표/근거)이 필수다 — 계획 없는 매매를 시스템이 거부한다.
  - 청산 후 복기(계획 준수 여부)를 기록하면, "계획을 지켰을 때 vs 어겼을 때"의
    성과 차이가 실제 숫자로 쌓인다. 이것이 지어낸 78% 대신 얻는 진짜 데이터다.

데이터: memory/trade_rules.json (체크리스트), memory/trade_journal.json (일지)
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MEMORY = ROOT / "memory"
RULES = MEMORY / "trade_rules.json"
JOURNAL = MEMORY / "trade_journal.json"

MIN_SAMPLE = 10  # 이보다 표본이 적으면 통계에 "표본 부족" 표시


def load_rules() -> dict:
    with open(RULES, encoding="utf-8") as f:
        return json.load(f)


def _journal() -> dict:
    if not JOURNAL.exists():
        return {"trades": []}
    with open(JOURNAL, encoding="utf-8") as f:
        return json.load(f)


def _save(j: dict) -> None:
    with open(JOURNAL, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=2)


def score(checked_ids: list[str]) -> dict:
    """체크된 항목 ID들 → 합계 점수. (산수일 뿐, 판단은 사용자의 것)"""
    rules = load_rules()
    total = max_total = 0
    for cat in rules["categories"]:
        for item in cat["items"]:
            max_total += item["points"]
            if item["id"] in checked_ids:
                total += item["points"]
    return {"score": total, "max": max_total,
            "threshold": rules["threshold"],
            "pass": total >= rules["threshold"]}


def open_trade(ticker: str, name: str, qty: float, price: float,
               stop_loss_pct: float, target_pct: float, reason: str,
               checked_ids: list[str] | None = None) -> dict:
    """매수 기록. 계획(손절/목표/근거)이 없으면 거부한다 — 이것이 규율이다."""
    if qty <= 0 or price <= 0:
        raise ValueError("수량과 가격은 양수여야 합니다")
    if not (0 < stop_loss_pct <= 50):
        raise ValueError("손절 기준(%)을 0~50 사이로 정하세요 — 계획 없는 매매는 기록할 수 없습니다")
    if target_pct <= 0:
        raise ValueError("목표 수익(%)을 정하세요 — 계획 없는 매매는 기록할 수 없습니다")
    if not reason.strip():
        raise ValueError("매수 근거를 한 줄이라도 적으세요 — 복기의 재료가 됩니다")

    sc = score(checked_ids or [])
    trade = {
        "id": uuid.uuid4().hex[:8],
        "date": date.today().isoformat(),
        "ticker": ticker.upper().strip(), "name": name,
        "qty": qty, "entry_price": price,
        "plan": {"stop_loss_pct": stop_loss_pct, "target_pct": target_pct,
                 "reason": reason.strip()},
        "checklist": {"score": sc["score"], "max": sc["max"],
                       "passed": sc["pass"], "checked": checked_ids or []},
        "status": "open",
        "close": None, "review": None,
    }
    j = _journal()
    j["trades"].append(trade)
    _save(j)
    return trade


def close_trade(trade_id: str, price: float) -> dict:
    if price <= 0:
        raise ValueError("청산 가격은 양수여야 합니다")
    j = _journal()
    t = next((x for x in j["trades"] if x["id"] == trade_id), None)
    if t is None:
        raise ValueError(f"매매 기록 없음: {trade_id}")
    if t["status"] != "open":
        raise ValueError("이미 청산된 기록입니다")
    pnl = (price - t["entry_price"]) * t["qty"]
    pnl_pct = round((price / t["entry_price"] - 1) * 100, 2)
    t["status"] = "closed"
    t["close"] = {"date": date.today().isoformat(), "price": price,
                  "pnl": round(pnl, 2), "pnl_pct": pnl_pct}
    _save(j)
    return t


def review_trade(trade_id: str, followed_plan: bool, note: str = "") -> dict:
    j = _journal()
    t = next((x for x in j["trades"] if x["id"] == trade_id), None)
    if t is None:
        raise ValueError(f"매매 기록 없음: {trade_id}")
    if t["status"] != "closed":
        raise ValueError("청산 후에 복기할 수 있습니다")
    t["review"] = {"followed_plan": bool(followed_plan), "note": note.strip()}
    _save(j)
    return t


def stats() -> dict:
    """본인 기록 기반 실통계. 표본이 적으면 그렇다고 말한다."""
    closed = [t for t in _journal()["trades"] if t["status"] == "closed"]
    n = len(closed)
    if n == 0:
        return {"n": 0, "note": "청산된 매매가 없습니다. 기록이 쌓이면 진짜 통계가 나옵니다."}

    wins = [t for t in closed if t["close"]["pnl"] > 0]
    losses = [t for t in closed if t["close"]["pnl"] <= 0]
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None  # noqa: E731

    reviewed = [t for t in closed if t.get("review")]
    followed = [t for t in reviewed if t["review"]["followed_plan"]]
    broke = [t for t in reviewed if not t["review"]["followed_plan"]]

    return {
        "n": n,
        "low_sample": n < MIN_SAMPLE,
        "low_sample_note": (f"표본 {n}건 — {MIN_SAMPLE}건 미만이라 통계적 의미가 약합니다"
                            if n < MIN_SAMPLE else None),
        "win_rate": round(len(wins) / n * 100, 1),
        "avg_win_pct": avg([t["close"]["pnl_pct"] for t in wins]),
        "avg_loss_pct": avg([t["close"]["pnl_pct"] for t in losses]),
        "total_pnl": round(sum(t["close"]["pnl"] for t in closed), 2),
        "plan_adherence": {
            "reviewed": len(reviewed),
            "followed_rate": (round(len(followed) / len(reviewed) * 100, 1)
                              if reviewed else None),
            "followed_avg_pct": avg([t["close"]["pnl_pct"] for t in followed]),
            "broke_avg_pct": avg([t["close"]["pnl_pct"] for t in broke]),
        },
        "checklist_effect": {
            "passed_avg_pct": avg([t["close"]["pnl_pct"] for t in closed
                                   if t["checklist"]["passed"]]),
            "failed_avg_pct": avg([t["close"]["pnl_pct"] for t in closed
                                   if not t["checklist"]["passed"]]),
        },
    }


def journal(limit: int = 20) -> list[dict]:
    return sorted(_journal()["trades"], key=lambda t: t["date"], reverse=True)[:limit]

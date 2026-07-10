"""finance/finance.py — Finance Center (4단계).

기능:
  - 수익/비용 장부 (memory/finance.json)
  - AI 사용료 자동 연동 (router의 ai_usage.json → 비용으로 집계)
  - 종합소득세 추정 (memory/tax_config.json 세율표 기반, 참고용)
  - 신고 일정 D-day

⚠ 세금 계산은 참고용 추정치다. 세액공제/기납부세액을 반영하지 않으며,
   실제 신고는 홈택스/세무사와 확인해야 한다.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MEMORY = ROOT / "memory"
LEDGER_FILE = MEMORY / "finance.json"
TAX_FILE = MEMORY / "tax_config.json"


# ── 장부 ──────────────────────────────────────────────

def _load_ledger() -> dict:
    if not LEDGER_FILE.exists():
        return {"entries": []}
    with open(LEDGER_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_ledger(data: dict) -> None:
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_entry(kind: str, amount: int, category: str, memo: str = "",
              on: str | None = None) -> dict:
    if kind not in ("income", "expense"):
        raise ValueError("kind는 income 또는 expense")
    if amount <= 0:
        raise ValueError("금액은 양수")
    entry = {
        "id": uuid.uuid4().hex[:8],
        "date": on or date.today().isoformat(),
        "kind": kind,
        "category": category,
        "amount": int(amount),
        "memo": memo,
    }
    data = _load_ledger()
    data["entries"].append(entry)
    _save_ledger(data)
    return entry


def delete_entry(entry_id: str) -> bool:
    data = _load_ledger()
    before = len(data["entries"])
    data["entries"] = [e for e in data["entries"] if e["id"] != entry_id]
    _save_ledger(data)
    return len(data["entries"]) < before


# ── AI 사용료 연동 ────────────────────────────────────

def ai_cost_krw(year: int) -> dict:
    """router가 기록한 ai_usage.json에서 해당 연도 실비용 집계."""
    usage_file = MEMORY / "ai_usage.json"
    if not usage_file.exists():
        return {"cost_krw": 0, "calls": 0, "unpriced": 0}
    calls = json.load(open(usage_file, encoding="utf-8"))["calls"]
    real = [c for c in calls
            if not c.get("dry_run") and c["time"].startswith(str(year))]
    return {
        "cost_krw": round(sum(c["cost_krw"] for c in real
                              if c.get("cost_krw") is not None), 2),
        "calls": len(real),
        "unpriced": sum(1 for c in real if c.get("cost_krw") is None),
    }


# ── 세금 추정 ────────────────────────────────────────

def load_tax_config() -> dict:
    with open(TAX_FILE, encoding="utf-8") as f:
        return json.load(f)


def calc_income_tax(taxable: float, cfg: dict | None = None) -> dict:
    """과세표준 → 산출세액 (과세표준 × 세율 − 누진공제) + 지방소득세."""
    cfg = cfg or load_tax_config()
    if taxable <= 0:
        return {"taxable": 0, "national": 0, "local": 0, "total": 0, "rate": 0}
    for b in cfg["brackets"]:
        if b["up_to"] is None or taxable <= b["up_to"]:
            national = taxable * b["rate"] - b["deduction"]
            break
    national = max(round(national), 0)
    local = round(national * cfg["local_income_tax_rate"])
    return {"taxable": round(taxable), "national": national, "local": local,
            "total": national + local, "rate": b["rate"]}


def next_deadlines(today: date | None = None) -> list[dict]:
    today = today or date.today()
    cfg = load_tax_config()
    out = []
    for f in cfg["filing_schedule"]:
        d = date(today.year, f["month"], f["day"])
        if d < today:
            d = date(today.year + 1, f["month"], f["day"])
        out.append({"name": f["name"], "date": d.isoformat(),
                    "d_day": (d - today).days})
    return sorted(out, key=lambda x: x["d_day"])


# ── 종합 요약 ────────────────────────────────────────

def summary(year: int | None = None) -> dict:
    year = year or date.today().year
    data = _load_ledger()
    entries = [e for e in data["entries"] if e["date"].startswith(str(year))]
    income = sum(e["amount"] for e in entries if e["kind"] == "income")
    expense = sum(e["amount"] for e in entries if e["kind"] == "expense")
    ai = ai_cost_krw(year)
    total_expense = expense + ai["cost_krw"]

    monthly = {}
    for e in entries:
        m = e["date"][:7]
        monthly.setdefault(m, {"income": 0, "expense": 0})
        monthly[m][e["kind"]] += e["amount"]

    cfg = load_tax_config()
    taxable = income - total_expense - cfg["income_deduction"]
    tax = calc_income_tax(taxable, cfg)

    this_month = date.today().isoformat()[:7]
    return {
        "year": year,
        "income": income,
        "expense": expense,
        "ai_cost": ai,
        "total_expense": round(total_expense, 2),
        "net": round(income - total_expense, 2),
        "this_month": monthly.get(this_month, {"income": 0, "expense": 0}),
        "monthly": dict(sorted(monthly.items())),
        "tax_estimate": tax,
        "tax_disclaimer": cfg["disclaimer"],
        "income_deduction": cfg["income_deduction"],
        "deadlines": next_deadlines(),
        "filing_notes": cfg.get("filing_notes", []),
        "recent": sorted(entries, key=lambda e: e["date"], reverse=True)[:10],
    }

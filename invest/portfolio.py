"""invest/portfolio.py — 투자센터 (5단계).

원칙 (docs/01):
  - JARVIS는 절대 매매 주문을 실행하지 않는다.
  - 매수/매도 추천을 하지 않는다. 정보 정리와 브리핑만 제공하며
    투자 판단과 책임은 사용자에게 있다.

기능: 보유 종목 관리, 손익 계산, 시세 갱신(수동/자동), 투자 일정 D-day.
데이터: memory/portfolio.json
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
FILE = MEMORY / "portfolio.json"

DISCLAIMER = ("JARVIS는 매매 주문을 실행하지 않으며 매수/매도 추천을 하지 않습니다. "
              "시세는 지연되거나 부정확할 수 있고, 투자 판단과 책임은 본인에게 있습니다.")


def _load() -> dict:
    if not FILE.exists():
        return {"holdings": [], "events": []}
    with open(FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 보유 종목 ─────────────────────────────────────────

def add_holding(ticker: str, name: str, qty: float, avg_price: float,
                currency: str = "KRW") -> dict:
    if qty <= 0 or avg_price <= 0:
        raise ValueError("수량과 평균단가는 양수여야 합니다")
    h = {"id": uuid.uuid4().hex[:8], "ticker": ticker.upper().strip(),
         "name": name, "qty": qty, "avg_price": avg_price,
         "currency": currency.upper(), "last_price": None, "price_time": None}
    data = _load()
    data["holdings"].append(h)
    _save(data)
    return h


def remove_holding(hid: str) -> bool:
    data = _load()
    before = len(data["holdings"])
    data["holdings"] = [h for h in data["holdings"] if h["id"] != hid]
    _save(data)
    return len(data["holdings"]) < before


def set_price(hid: str, price: float, source: str = "manual") -> dict | None:
    if price <= 0:
        raise ValueError("가격은 양수여야 합니다")
    data = _load()
    for h in data["holdings"]:
        if h["id"] == hid:
            h["last_price"] = price
            h["price_time"] = datetime.now().isoformat(timespec="seconds") + f" ({source})"
            _save(data)
            return h
    return None


# ── 일정 ─────────────────────────────────────────────

def add_event(on: str, name: str) -> dict:
    date.fromisoformat(on)  # 형식 검증
    e = {"id": uuid.uuid4().hex[:8], "date": on, "name": name}
    data = _load()
    data["events"].append(e)
    _save(data)
    return e


def remove_event(eid: str) -> bool:
    data = _load()
    before = len(data["events"])
    data["events"] = [e for e in data["events"] if e["id"] != eid]
    _save(data)
    return len(data["events"]) < before


# ── 요약 ─────────────────────────────────────────────

def summary() -> dict:
    data = _load()
    today = date.today()
    holdings = []
    totals: dict[str, dict] = {}
    for h in data["holdings"]:
        cost = h["qty"] * h["avg_price"]
        cur = h["currency"]
        t = totals.setdefault(cur, {"cost": 0.0, "value": 0.0, "priced": True})
        t["cost"] += cost
        row = dict(h)
        if h["last_price"]:
            value = h["qty"] * h["last_price"]
            row["value"] = round(value, 2)
            row["pnl"] = round(value - cost, 2)
            row["pnl_pct"] = round((value / cost - 1) * 100, 2)
            t["value"] += value
        else:
            row["value"] = row["pnl"] = row["pnl_pct"] = None
            t["priced"] = False
        holdings.append(row)

    for cur, t in totals.items():
        t["cost"] = round(t["cost"], 2)
        if t["priced"] and t["cost"]:
            t["value"] = round(t["value"], 2)
            t["pnl"] = round(t["value"] - t["cost"], 2)
            t["pnl_pct"] = round((t["value"] / t["cost"] - 1) * 100, 2)
        else:
            t["value"] = t["pnl"] = t["pnl_pct"] = None

    events = []
    for e in sorted(data["events"], key=lambda x: x["date"]):
        d = date.fromisoformat(e["date"])
        if d >= today:
            events.append({**e, "d_day": (d - today).days})

    return {"holdings": holdings, "totals": totals, "events": events,
            "disclaimer": DISCLAIMER}

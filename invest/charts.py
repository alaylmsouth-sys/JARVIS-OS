"""invest/charts.py — 주요 종목 차트 보드 데이터.

memory/watchlist.json의 종목들에 대해 3개월 일봉 종가 시리즈를 수집한다.
야후 호출을 아끼기 위해 하루 1회 캐시(memory/chart_cache.json)한다.
"""
from __future__ import annotations
import json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from invest.screener import HEADERS  # noqa: E402
import requests  # noqa: E402

MEMORY = ROOT / "memory"
WATCH = MEMORY / "watchlist.json"
CACHE = MEMORY / "chart_cache.json"
MAX_POINTS = 60  # 프론트로 보내는 최대 점 수


def downsample(xs: list[float], n: int = MAX_POINTS) -> list[float]:
    if len(xs) <= n:
        return [round(x, 4) for x in xs]
    step = len(xs) / n
    return [round(xs[int(i * step)], 4) for i in range(n - 1)] + [round(xs[-1], 4)]


def change_pct(closes: list[float]) -> float | None:
    if len(closes) < 2 or closes[-2] == 0:
        return None
    return round((closes[-1] / closes[-2] - 1) * 100, 2)


def _fetch_series(ticker: str) -> dict:
    r = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        params={"range": "3mo", "interval": "1d"},
        headers=HEADERS, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    res = r.json()["chart"]["result"][0]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    if len(closes) < 5:
        raise RuntimeError("데이터 부족")
    return {"series": downsample(closes),
            "price": round(closes[-1], 4),
            "change_pct": change_pct(closes),
            "currency": res["meta"].get("currency", "")}


def board(refresh: bool = False) -> dict:
    today = date.today().isoformat()
    if not refresh and CACHE.exists():
        c = json.loads(CACHE.read_text(encoding="utf-8"))
        if c.get("date") == today:
            return c
    watch = json.loads(WATCH.read_text(encoding="utf-8"))
    items = []
    for w in watch["tickers"][:15]:
        try:
            items.append({**w, **_fetch_series(w["ticker"]), "error": None})
        except Exception as e:
            items.append({**w, "series": [], "price": None,
                          "change_pct": None, "currency": "", "error": str(e)[:120]})
    out = {"date": today, "items": items,
           "note": "3개월 일봉 · 하루 1회 갱신 · 종목 목록은 memory/watchlist.json에서 수정"}
    CACHE.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out

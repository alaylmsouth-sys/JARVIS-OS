"""invest/detail.py — 종목 상세 (캔들, 이동평균, 지표, 뉴스 요약).

- 일봉 1년치로 MA5/20/120 오버레이 + RSI/MACD/거래량배수/52주 위치 계산 (전부 산수)
- 5분봉(당일) 지원
- 뉴스: 야후 검색 API의 실제 헤드라인 → AI는 그 헤드라인만 요약 (추천 금지)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from invest.screener import HEADERS, sma, rsi  # noqa: E402

CANDLES_SHOWN = 60  # 화면에 보여줄 캔들 수


def _fetch_chart(ticker: str, rng: str, interval: str) -> dict:
    r = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        params={"range": rng, "interval": interval},
        headers=HEADERS, timeout=8)
    if r.status_code != 200:
        raise RuntimeError(f"시세 조회 실패 HTTP {r.status_code}")
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    ts = res["timestamp"]
    candles = []
    for i in range(len(ts)):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        candles.append({"t": ts[i], "o": round(o, 4), "h": round(h, 4),
                        "l": round(l, 4), "c": round(c, 4),
                        "v": q["volume"][i] or 0})
    if len(candles) < 5:
        raise RuntimeError("데이터 부족")
    return {"candles": candles, "currency": res["meta"].get("currency", "")}


def ema(xs: list[float], n: int) -> list[float]:
    if not xs:
        return []
    k = 2 / (n + 1)
    out = [xs[0]]
    for x in xs[1:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def macd(closes: list[float]) -> dict | None:
    if len(closes) < 35:
        return None
    e12, e26 = ema(closes, 12), ema(closes, 26)
    line = [a - b for a, b in zip(e12, e26)]
    signal = ema(line, 9)
    return {"macd": round(line[-1], 4), "signal": round(signal[-1], 4),
            "hist": round(line[-1] - signal[-1], 4)}


def _ma_series(closes: list[float], n: int, count: int) -> list[float | None]:
    """마지막 count개 캔들에 정렬된 n일 이동평균 시리즈."""
    out = []
    for i in range(len(closes) - count, len(closes)):
        window = closes[: i + 1]
        out.append(round(sum(window[-n:]) / n, 4) if len(window) >= n else None)
    return out


def detail(ticker: str, interval: str = "1d") -> dict:
    if interval == "5m":
        data = _fetch_chart(ticker, "1d", "5m")
        return {"ticker": ticker.upper(), "interval": "5m",
                "currency": data["currency"],
                "candles": data["candles"][-CANDLES_SHOWN:],
                "ma": {}, "indicators": None,
                "note": "당일 5분봉 (지연 시세 가능)"}

    data = _fetch_chart(ticker, "1y", "1d")
    candles = data["candles"]
    closes = [c["c"] for c in candles]
    shown = candles[-CANDLES_SHOWN:]
    n = len(shown)
    vol_avg = sma([c["v"] for c in candles[:-1]], 20)
    hi52, lo52 = max(c["h"] for c in candles), min(c["l"] for c in candles)
    price = closes[-1]
    return {
        "ticker": ticker.upper(), "interval": "1d",
        "currency": data["currency"],
        "candles": shown,
        "ma": {"ma5": _ma_series(closes, 5, n),
                "ma20": _ma_series(closes, 20, n),
                "ma120": _ma_series(closes, 120, n)},
        "indicators": {
            "price": round(price, 4),
            "rsi14": rsi(closes),
            "macd": macd(closes),
            "volume_ratio_20d": round(candles[-1]["v"] / vol_avg, 2) if vol_avg else None,
            "high_52w": round(hi52, 4), "low_52w": round(lo52, 4),
            "pos_52w_pct": round((price - lo52) / (hi52 - lo52) * 100, 1)
                            if hi52 > lo52 else None,
        },
        "note": "일봉 60개 표시 · 이동평균은 1년 데이터로 계산 · 캔들: 상승 빨강/하락 파랑",
    }


def news(ticker: str) -> list[dict]:
    """야후 검색 API의 실제 뉴스 헤드라인 (한국 종목은 영문 위주일 수 있음)."""
    r = requests.get(
        "https://query1.finance.yahoo.com/v1/finance/search",
        params={"q": ticker, "newsCount": 8, "quotesCount": 0},
        headers=HEADERS, timeout=8)
    if r.status_code != 200:
        raise RuntimeError(f"뉴스 조회 실패 HTTP {r.status_code}")
    out = []
    for item in r.json().get("news", [])[:8]:
        out.append({"title": item.get("title", ""),
                     "publisher": item.get("publisher", ""),
                     "link": item.get("link", "")})
    return out


ISSUE_SYSTEM = ("너는 투자자의 정보 비서다. 제공된 실제 뉴스 헤드라인만 근거로 "
                "해당 종목의 최근 이슈를 한국어 3~5문장으로 중립 요약한다. "
                "규칙: 헤드라인에 없는 내용을 지어내지 않는다. 매수/매도 의견과 "
                "가격 전망을 말하지 않는다. 마지막에 '헤드라인 기반 요약이며 "
                "원문 확인을 권장합니다'를 붙인다.")


def issue_summary(ticker: str, headlines: list[dict]) -> str:
    from router.router import route, load_table, TABLE_FILE
    t = load_table()
    if "issue_brief" not in t["routes"]:
        base = t["routes"]["script"]
        t["routes"]["issue_brief"] = {"description": "종목 이슈 요약 (헤드라인 기반)",
                                       "provider": base["provider"],
                                       "model": base["model"],
                                       "system": ISSUE_SYSTEM, "fallback": None}
        with open(TABLE_FILE, "w", encoding="utf-8") as f:
            json.dump(t, f, ensure_ascii=False, indent=2)
    lines = "\n".join(f"- {h['title']} ({h['publisher']})" for h in headlines if h["title"])
    if not lines:
        return "요약할 헤드라인이 없습니다."
    return route("issue_brief", f"종목 {ticker}의 최근 뉴스 헤드라인:\n{lines}")["result"]["text"]

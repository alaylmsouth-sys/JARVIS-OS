"""invest/screener.py — 자동 분석 (지표 계산 + 체크리스트 자동 채점).

하는 일:
  - 야후 파이낸스에서 일봉 1년치를 받아 이동평균(5/20/120), 거래량 배수,
    RSI(14)를 **계산**한다. 전부 산수이며 예측이 아니다.
  - 계산 결과를 매매 체크리스트의 차트/거래량 항목(c1~c4, v1)에 매핑해
    자동 채점한다. 뉴스/재무/수급 등 판단이 필요한 항목은 사람 몫으로 남긴다.

하지 않는 일:
  - 매수/매도 추천, 확률/목표가 생성.

⚠ 일봉 기준(장중 실시간 아님), 시세 지연/오류 가능. 야후 실호출은 미검증.
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HEADERS = {"User-Agent": "Mozilla/5.0 (JARVIS-OS personal analysis)"}
VOLUME_SPIKE = 2.0  # 20일 평균 대비 이 배수 이상이면 "거래량 급증"으로 표시


# ── 데이터 수집 (네트워크) ────────────────────────────

def fetch_daily(ticker: str) -> dict:
    """일봉 1년치: {"closes": [...], "volumes": [...]}"""
    r = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        params={"range": "1y", "interval": "1d"},
        headers=HEADERS, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"시세 조회 실패 {r.status_code} — 티커를 확인하세요 "
                           f"(한국: 005930.KS / 미국: NVDA)")
    try:
        res = r.json()["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        closes = [c for c in q["close"] if c is not None]
        volumes = [v for v in q["volume"] if v is not None]
        if len(closes) < 30:
            raise RuntimeError("데이터가 부족합니다 (신규 상장 등)")
        return {"closes": closes, "volumes": volumes,
                "currency": res["meta"].get("currency", "")}
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"시세 응답 해석 실패: {e}")


# ── 지표 계산 (순수 산수 — 단위 테스트 대상) ──────────

def sma(xs: list[float], n: int) -> float | None:
    return round(sum(xs[-n:]) / n, 4) if len(xs) >= n else None


def rsi(closes: list[float], n: int = 14) -> float | None:
    if len(closes) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(-n, 0):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return round(100 - 100 / (1 + rs), 1)


def analyze(closes: list[float], volumes: list[float]) -> dict:
    """계산 가능한 사실만 반환. True/False/None(데이터 부족)."""
    price = closes[-1]
    ma5, ma20, ma120 = sma(closes, 5), sma(closes, 20), sma(closes, 120)
    ma20_prev = sma(closes[:-5], 20)  # 5거래일 전의 20일선
    vol_avg20 = sma(volumes[:-1], 20)
    vol_ratio = round(volumes[-1] / vol_avg20, 2) if vol_avg20 else None

    facts = {
        "price": round(price, 4),
        "ma5": ma5, "ma20": ma20, "ma120": ma120,
        "rsi14": rsi(closes),
        "volume_ratio_20d": vol_ratio,
        "checks": {
            "ma5_above_ma20": (ma5 > ma20) if ma5 and ma20 else None,
            "ma20_rising": (ma20 > ma20_prev) if ma20 and ma20_prev else None,
            "above_ma120": (price > ma120) if ma120 else None,
            "uptrend": (price > ma20 and ma20 > ma20_prev)
                       if ma20 and ma20_prev else None,
            "volume_spike": (vol_ratio >= VOLUME_SPIKE) if vol_ratio else None,
        },
    }
    return facts


# 체크리스트 항목 매핑: 계산 결과 → trade_rules.json의 항목 id
CHECK_MAP = {
    "ma5_above_ma20": "c1",
    "ma20_rising": "c2",
    "above_ma120": "c3",
    "uptrend": "c4",
    "volume_spike": "v1",
}


def screen(ticker: str) -> dict:
    """티커 하나 자동 분석 → 사실 + 자동 체크된 항목 id 목록."""
    data = fetch_daily(ticker)
    facts = analyze(data["closes"], data["volumes"])
    auto_checked = [CHECK_MAP[k] for k, v in facts["checks"].items() if v is True]
    return {
        "ticker": ticker.upper(),
        "currency": data["currency"],
        "facts": facts,
        "auto_checked": auto_checked,
        "human_items": "뉴스/재무/수급/시장/계획 항목은 직접 확인하세요",
        "disclaimer": ("일봉 기준 자동 계산이며 지연/오류가 있을 수 있습니다. "
                        "규칙 충족 표시는 사실 확인일 뿐 매수 추천이 아닙니다."),
    }

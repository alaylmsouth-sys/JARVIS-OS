"""invest/prices.py — 시세 조회.

야후 파이낸스 공개 엔드포인트 사용 (API 키 불필요, 지연 시세).
한국 주식은 티커에 .KS(코스피)/.KQ(코스닥) 접미사: 예) 005930.KS (삼성전자)
미국 주식은 그대로: 예) NVDA, AAPL

⚠ 개발 환경에서 실호출 미검증 (docs/07 참고). 실패 시 수동 입력을 사용하세요.
"""
from __future__ import annotations
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (JARVIS-OS personal portfolio tracker)"}


def fetch_price(ticker: str) -> dict:
    """반환: {"price": float, "currency": str} / 실패 시 RuntimeError"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    try:
        r = requests.get(url, params={"range": "1d", "interval": "1d"},
                         headers=HEADERS, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"시세 조회 실패 {r.status_code}")
        meta = r.json()["chart"]["result"][0]["meta"]
        return {"price": float(meta["regularMarketPrice"]),
                "currency": meta.get("currency", "")}
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"시세 응답 해석 실패: {e}")
    except requests.RequestException as e:
        raise RuntimeError(f"시세 조회 네트워크 오류: {e}")

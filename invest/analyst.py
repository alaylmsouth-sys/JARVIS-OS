"""invest/analyst.py — AI 브리핑.

포트폴리오 요약(+선택: 사용자가 붙여넣은 뉴스)을 바탕으로 중립적 브리핑 생성.
매수/매도 추천은 시스템 프롬프트로 금지한다. 라우팅 규칙(invest_brief)이
없으면 script 라우트의 provider/model을 복사해 자동 등록한다.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from router.router import route, load_table, TABLE_FILE  # noqa: E402
from invest.portfolio import summary  # noqa: E402

SYSTEM = ("너는 개인 투자자의 정보 비서다. 보유 종목 현황과 제공된 뉴스를 바탕으로 "
          "중립적인 한국어 브리핑을 작성한다. 규칙: (1) 매수/매도/보유 추천을 절대 하지 않는다. "
          "(2) 가격 예측을 하지 않는다. (3) 사실과 확인 필요한 사항을 구분해 표시한다. "
          "(4) 마지막에 '투자 판단과 책임은 본인에게 있습니다'를 명시한다. "
          "형식: 보유 현황 요약 / 관련 소식(제공된 경우) / 확인해볼 일정·공시 순서로 간결하게.")


def ensure_route() -> None:
    t = load_table()
    if "invest_brief" in t["routes"]:
        return
    base = t["routes"]["script"]
    t["routes"]["invest_brief"] = {
        "description": "투자 브리핑 (추천 금지)",
        "provider": base["provider"], "model": base["model"],
        "system": SYSTEM, "fallback": None,
    }
    with open(TABLE_FILE, "w", encoding="utf-8") as f:
        json.dump(t, f, ensure_ascii=False, indent=2)


def brief(news_text: str = "", dry_run: bool = False) -> str:
    ensure_route()
    s = summary()
    lines = [f"- {h['name']}({h['ticker']}): {h['qty']}주, 평단 {h['avg_price']}, "
             f"현재가 {h['last_price'] or '미입력'}" for h in s["holdings"]]
    prompt = "보유 종목:\n" + ("\n".join(lines) or "(없음)")
    if s["events"]:
        prompt += "\n\n예정 일정:\n" + "\n".join(
            f"- {e['date']} {e['name']} (D-{e['d_day']})" for e in s["events"][:5])
    if news_text.strip():
        prompt += "\n\n사용자가 제공한 뉴스/자료:\n" + news_text.strip()[:4000]
    return route("invest_brief", prompt, dry_run=dry_run)["result"]["text"]

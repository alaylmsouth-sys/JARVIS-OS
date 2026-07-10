"""투자센터 테스트. 실행: python tests/test_invest.py"""
import sys
from datetime import date, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from invest.portfolio import (add_holding, remove_holding, set_price,
                              add_event, remove_event, summary)
from invest.analyst import brief, ensure_route
from router.router import load_table

def main():
    # 1. 종목 추가 + 손익 계산 검증: 10주 x 평단 70,000, 현재가 80,000 → +100,000 (+14.29%)
    h = add_holding("005930.KS", "삼성전자", 10, 70000)
    set_price(h["id"], 80000)
    s = summary()
    row = next(x for x in s["holdings"] if x["id"] == h["id"])
    assert row["pnl"] == 100000, f"손익 계산 오류: {row['pnl']}"
    assert row["pnl_pct"] == 14.29
    assert s["totals"]["KRW"]["cost"] >= 700000

    # 2. 시세 미입력 종목 → 손익 None (가짜 숫자 금지)
    h2 = add_holding("NVDA", "엔비디아", 2, 100, "USD")
    s = summary()
    row2 = next(x for x in s["holdings"] if x["id"] == h2["id"])
    assert row2["pnl"] is None
    assert s["totals"]["USD"]["pnl"] is None

    # 3. 일정 D-day
    future = (date.today() + timedelta(days=7)).isoformat()
    e = add_event(future, "실적 발표")
    s = summary()
    ev = next(x for x in s["events"] if x["id"] == e["id"])
    assert ev["d_day"] == 7

    # 4. AI 브리핑 (dry-run) + 라우트 자동 등록
    ensure_route()
    assert "invest_brief" in load_table()["routes"]
    text = brief(dry_run=True)
    assert text, "브리핑 없음"

    # 5. 잘못된 입력 거부 + 정리
    try:
        add_holding("X", "x", -1, 100); raise AssertionError("음수 수량 거부 실패")
    except ValueError:
        pass
    try:
        set_price(h["id"], 0); raise AssertionError("0원 시세 거부 실패")
    except ValueError:
        pass
    assert remove_holding(h["id"]) and remove_holding(h2["id"]) and remove_event(e["id"])

    print("✅ 투자센터 테스트 5/5 통과")

if __name__ == "__main__":
    main()

"""매매 규율 시스템 테스트. 실행: python tests/test_discipline.py"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from invest.discipline import (score, open_trade, close_trade, review_trade,
                               stats, _journal, _save)

def main():
    backup = _journal()
    try:
        _save({"trades": []})

        # 1. 점수 계산 (규칙 파일의 항목 합산)
        sc = score(["c1", "c2", "v1"])
        assert sc["score"] == 20, f"점수 계산 오류: {sc['score']}"
        assert sc["pass"] is False  # 기준 80점 미달

        # 2. 계획 없는 매매 거부 (핵심 규율)
        for bad in [dict(stop_loss_pct=0), dict(target_pct=0), dict(reason="  ")]:
            kw = dict(ticker="T", name="t", qty=1, price=100,
                      stop_loss_pct=3, target_pct=7, reason="근거")
            kw.update(bad)
            try:
                open_trade(**kw); raise AssertionError(f"거부 실패: {bad}")
            except ValueError:
                pass

        # 3. 매수→청산 손익: 10주 @1000 → @1100 = +1000원 (+10%)
        t = open_trade("005930.KS", "삼성전자", 10, 1000, 3, 7, "테스트", ["c1"])
        t = close_trade(t["id"], 1100)
        assert t["close"]["pnl"] == 1000 and t["close"]["pnl_pct"] == 10.0

        # 4. 복기 → 통계 (실기록 기반)
        review_trade(t["id"], True, "계획대로 익절")
        t2 = open_trade("X", "x", 10, 1000, 3, 7, "테스트2")
        close_trade(t2["id"], 950)
        review_trade(t2["id"], False, "손절 못 지킴")
        s = stats()
        assert s["n"] == 2 and s["win_rate"] == 50.0
        assert s["low_sample"] is True          # 표본 부족을 정직하게 표시
        assert s["plan_adherence"]["followed_avg_pct"] == 10.0
        assert s["plan_adherence"]["broke_avg_pct"] == -5.0

        # 5. 중복 청산/미청산 복기 거부
        try:
            close_trade(t["id"], 1); raise AssertionError
        except ValueError:
            pass

        print("✅ 매매 규율 테스트 5/5 통과")
    finally:
        _save(backup)

if __name__ == "__main__":
    main()

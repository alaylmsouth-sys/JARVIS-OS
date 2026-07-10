"""Finance Center 테스트. 실행: python tests/test_finance.py"""
import sys
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from finance.finance import (add_entry, delete_entry, calc_income_tax,
                             next_deadlines, summary, load_tax_config)

def main():
    cfg = load_tax_config()

    # 1. 국세청 공식 예시 검증: 과세표준 3,000만원 → 324만원
    t = calc_income_tax(30_000_000, cfg)
    assert t["national"] == 3_240_000, f"국세청 예시 불일치: {t['national']}"
    assert t["local"] == 324_000
    # 경계값: 1,400만원 이하 6%
    assert calc_income_tax(14_000_000, cfg)["national"] == 840_000
    # 0 이하 → 세금 0
    assert calc_income_tax(-5, cfg)["total"] == 0

    # 2. 장부 기록/삭제
    e1 = add_entry("income", 500_000, "유튜브", "테스트 수익")
    e2 = add_entry("expense", 120_000, "장비", "테스트 비용")
    s = summary(date.today().year)
    assert s["income"] >= 500_000 and s["expense"] >= 120_000
    assert delete_entry(e1["id"]) and delete_entry(e2["id"])

    # 3. 요약 무결성: 순이익 = 수익 - 총비용
    s = summary(date.today().year)
    assert abs(s["net"] - (s["income"] - s["total_expense"])) < 0.01

    # 4. 신고 일정: 항상 미래 날짜, D-day 오름차순
    ds = next_deadlines()
    assert all(d["d_day"] >= 0 for d in ds)
    assert ds == sorted(ds, key=lambda x: x["d_day"])

    # 5. 잘못된 입력 거부
    for bad in [("보너스", 1000), ("income", -5)]:
        try:
            add_entry(bad[0], bad[1], "x"); raise AssertionError("거부 실패")
        except ValueError:
            pass

    print("✅ Finance Center 테스트 5/5 통과")

if __name__ == "__main__":
    main()

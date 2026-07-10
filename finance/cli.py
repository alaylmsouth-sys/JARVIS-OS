"""사용법:
  python -m finance.cli add income 150000 유튜브수익 "6월 애드센스"
  python -m finance.cli add expense 12000 AI사용료 "fal.ai 충전"
  python -m finance.cli summary
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from finance.finance import add_entry, summary

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("kind", choices=["income", "expense"])
    a.add_argument("amount", type=int)
    a.add_argument("category")
    a.add_argument("memo", nargs="?", default="")
    sub.add_parser("summary")
    args = p.parse_args()

    if args.cmd == "add":
        e = add_entry(args.kind, args.amount, args.category, args.memo)
        label = "수익" if e["kind"] == "income" else "비용"
        print(f"✅ {label} 기록: {e['date']} {e['category']} {e['amount']:,}원 {e['memo']}")
    else:
        s = summary()
        print(f"── {s['year']}년 재무 요약 ──")
        print(f"수익      {s['income']:>14,.0f}원")
        print(f"비용(장부) {s['expense']:>13,.0f}원")
        print(f"AI 사용료  {s['ai_cost']['cost_krw']:>13,.0f}원 ({s['ai_cost']['calls']}회, 미산정 {s['ai_cost']['unpriced']}회)")
        print(f"순이익    {s['net']:>14,.0f}원")
        t = s['tax_estimate']
        print(f"예상 종합소득세(참고용): {t['total']:,}원 (국세 {t['national']:,} + 지방세 {t['local']:,})")
        for d in s['deadlines'][:2]:
            print(f"📅 {d['name']} — {d['date']} (D-{d['d_day']})")

if __name__ == "__main__":
    main()

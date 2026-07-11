"""스크리너 계산 테스트 (네트워크 없이). 실행: python tests/test_screener.py"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from invest.screener import sma, rsi, analyze, CHECK_MAP

def main():
    # 1. SMA: 1..10의 5일 평균 = 8
    assert sma(list(map(float, range(1, 11))), 5) == 8.0
    assert sma([1.0, 2.0], 5) is None  # 데이터 부족 → None (지어내지 않음)

    # 2. RSI: 연속 상승 → 100 / 연속 하락 → 0
    up = [float(i) for i in range(1, 20)]
    assert rsi(up) == 100.0
    down = [float(i) for i in range(20, 1, -1)]
    assert rsi(down) == 0.0

    # 3. 상승 시나리오: 130일 연속 상승 + 마지막날 거래량 3배
    closes = [100 + i * 0.5 for i in range(130)]
    volumes = [1000.0] * 129 + [3000.0]
    f = analyze(closes, volumes)
    c = f["checks"]
    assert c["ma5_above_ma20"] and c["ma20_rising"] and c["above_ma120"] and c["uptrend"]
    assert c["volume_spike"] is True and f["volume_ratio_20d"] == 3.0

    # 4. 하락 시나리오: 전부 False
    closes_d = [200 - i * 0.5 for i in range(130)]
    f2 = analyze(closes_d, [1000.0] * 130)
    c2 = f2["checks"]
    assert not c2["ma5_above_ma20"] and not c2["ma20_rising"] and not c2["above_ma120"]

    # 5. 매핑 무결성: trade_rules.json에 실제 존재하는 id인가
    import json
    rules = json.load(open(ROOT / "memory/trade_rules.json", encoding="utf-8"))
    all_ids = [i["id"] for cat in rules["categories"] for i in cat["items"]]
    assert all(v in all_ids for v in CHECK_MAP.values()), "매핑된 id가 규칙에 없음"

    print("✅ 스크리너 계산 테스트 5/5 통과")

if __name__ == "__main__":
    main()

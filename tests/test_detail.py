"""종목 상세 계산 테스트. 실행: python tests/test_detail.py"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from invest.detail import ema, macd, _ma_series

def main():
    # 1. EMA: 상수 수열 → 그대로 / 길이 보존
    assert ema([5.0]*10, 3) == [5.0]*10
    assert len(ema(list(map(float, range(50))), 12)) == 50

    # 2. MACD: 상승 추세 → macd 양수 / 데이터 부족 → None
    up = [100 + i for i in range(60)]
    m = macd(up)
    assert m and m["macd"] > 0
    assert macd([1.0]*10) is None

    # 3. MA 시리즈 정렬: 마지막 값 = 전체 SMA와 일치, 데이터 부족 구간 None
    closes = list(map(float, range(1, 31)))  # 1..30
    s = _ma_series(closes, 20, 25)
    assert len(s) == 25
    assert s[-1] == sum(closes[-20:]) / 20   # 21.5? -> 30..11 avg = 20.5
    assert s[0] is None or isinstance(s[0], float)
    early = _ma_series(closes, 120, 25)
    assert all(v is None for v in early)      # 120일치 없음 → 전부 None (지어내지 않음)

    print("✅ 종목 상세 계산 테스트 4/4 통과")

if __name__ == "__main__":
    main()

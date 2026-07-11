"""차트 보드 계산 테스트. 실행: python tests/test_charts.py"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from invest.charts import downsample, change_pct

def main():
    # 1. 다운샘플: 200점 → 60점, 시작/끝 보존
    xs = [float(i) for i in range(200)]
    d = downsample(xs)
    assert len(d) == 60 and d[0] == 0.0 and d[-1] == 199.0
    # 짧으면 그대로
    assert downsample([1.0, 2.0]) == [1.0, 2.0]

    # 2. 등락률: 100→110 = +10%
    assert change_pct([100.0, 110.0]) == 10.0
    assert change_pct([50.0]) is None  # 데이터 부족 → None

    # 3. watchlist 파일 무결성
    import json
    w = json.load(open(ROOT/"memory/watchlist.json", encoding="utf-8"))
    assert len(w["tickers"]) == 10 and all("ticker" in t for t in w["tickers"])

    print("✅ 차트 보드 테스트 3/3 통과")

if __name__ == "__main__":
    main()

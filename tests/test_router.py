"""AI Router 테스트 (키 없이 dry-run으로 검증). 실행: python tests/test_router.py"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from router.router import route, usage_summary, load_table

def main():
    # 1. 라우팅 규칙 로드
    table = load_table()
    assert "script" in table["routes"], "script 라우트 없음"

    # 2. dry-run 호출
    out = route("script", "테스트: AI가 세상을 바꾸는 이유", dry_run=True)
    assert out["result"]["text"], "응답 텍스트 없음"
    assert out["usage"]["dry_run"] is True

    # 3. 사용 기록이 파일에 저장되었는지
    usage = json.load(open(ROOT/"memory/ai_usage.json", encoding="utf-8"))
    assert len(usage["calls"]) >= 1, "호출 기록 저장 안 됨"

    # 4. 가격 미설정 시 비용 None 처리
    assert out["usage"]["cost_krw"] is None, "가격 미설정인데 비용이 계산됨"

    # 5. 잘못된 작업 유형 거부
    try:
        route("없는작업", "x", dry_run=True)
        raise AssertionError("잘못된 task를 거부하지 않음")
    except ValueError:
        pass

    # 6. 요약 함수
    s = usage_summary()
    assert s["total_calls"] >= 1

    print("✅ AI Router 테스트 6/6 통과")

if __name__ == "__main__":
    main()

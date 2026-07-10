"""업로더 안전장치 테스트 (네트워크 없이 원칙 검증). 실행: python tests/test_uploader.py"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from video.uploader import upload

QUEUE = ROOT / "memory" / "approval_queue.json"

def main():
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    backup = json.dumps(q, ensure_ascii=False)

    # 테스트 항목 주입
    q["items"].insert(0, {"id":"test-guard","type":"video","title":"가드 테스트",
                          "status":"pending","tags":[]})
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        # 1. 승인 안 된 항목 → 업로드 거부 (핵심 원칙)
        try:
            upload("test-guard"); raise AssertionError("미승인 업로드가 통과됨!")
        except PermissionError:
            pass

        # 2. 없는 항목 → 거부
        try:
            upload("no-such-item"); raise AssertionError("없는 항목 통과됨")
        except ValueError:
            pass

        # 3. 잘못된 privacy → 거부
        q2 = json.loads(QUEUE.read_text(encoding="utf-8"))
        q2["items"][0]["status"] = "approved"
        QUEUE.write_text(json.dumps(q2, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            upload("test-guard", privacy="everyone"); raise AssertionError("잘못된 privacy 통과됨")
        except ValueError:
            pass

        # 4. 승인됐지만 영상 파일 없음 → 명확한 오류 (토큰 검사 전에 파일부터)
        try:
            upload("test-guard"); raise AssertionError("파일 없는 업로드 통과됨")
        except FileNotFoundError:
            pass

        print("✅ 업로더 안전장치 테스트 4/4 통과")
    finally:
        QUEUE.write_text(backup, encoding="utf-8")

if __name__ == "__main__":
    main()

"""영상 파이프라인 테스트 (dry-run). 실행: python tests/test_pipeline.py"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from video.pipeline import run

def main():
    item = run("테스트 파이프라인", dry_run=True)
    job = ROOT / "video" / "output" / item["id"]

    # 1. 산출물 존재
    for f in ["final.mp4", "thumbnail.jpg", "subtitles.srt", "scenes.json", "script.txt"]:
        assert (job / f).exists(), f"{f} 없음"

    # 2. 영상 스펙 (1080x1920, 오디오 포함)
    p = subprocess.run(["ffprobe","-v","quiet","-print_format","json",
                        "-show_streams", str(job/"final.mp4")],
                       capture_output=True, text=True, check=True)
    streams = json.loads(p.stdout)["streams"]
    v = next(s for s in streams if s["codec_type"]=="video")
    assert (v["width"], v["height"]) == (1080, 1920), "해상도 오류"
    assert any(s["codec_type"]=="audio" for s in streams), "오디오 트랙 없음"

    # 3. 결재함 등록 + pending 상태 (자동 업로드 없음 원칙)
    q = json.load(open(ROOT/"memory/approval_queue.json", encoding="utf-8"))
    reg = next(i for i in q["items"] if i["id"]==item["id"])
    assert reg["status"] == "pending", "승인 대기 상태가 아님"

    # 4. Quality Inspector가 무음을 정직하게 감지
    assert reg["quality"]["음성"] < 100, "무음인데 음성 만점"
    assert any("무음" in w for w in reg["warnings"]), "무음 경고 없음"

    print("✅ 영상 파이프라인 테스트 4/4 통과")

if __name__ == "__main__":
    main()

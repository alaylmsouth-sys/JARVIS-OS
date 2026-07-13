"""성과 분석 테스트 (네트워크 없이 원칙 검증). 실행: python tests/test_analytics.py"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from video import analytics

QUEUE = ROOT / "memory" / "approval_queue.json"
PERF = ROOT / "memory" / "video_performance.json"
SCORE = ROOT / "memory" / "scoreboard.json"


def main():
    backups = {p: (p.read_text(encoding="utf-8") if p.exists() else None)
               for p in (QUEUE, PERF, SCORE)}
    try:
        # 준비: 결재함에 테스트 항목 3종 주입
        q = json.loads(QUEUE.read_text(encoding="utf-8"))
        q["items"] = [
            {"id": "up-1", "status": "uploaded", "title": "업로드작 A",
             "quality": {"대본": 90, "음성": 80, "영상": 70, "썸네일": 60},
             "youtube": {"video_id": "VID1", "url": "https://youtu.be/VID1",
                         "uploaded_at": "2026-07-10 09:00"}},
            {"id": "up-2", "status": "uploaded", "title": "업로드작 B",
             "quality": {"대본": 70, "음성": 60, "영상": 90},
             "youtube": {"video_id": "VID2", "url": "https://youtu.be/VID2"}},
            {"id": "pend-1", "status": "pending", "title": "미승인작",
             "youtube": {"video_id": "NOPE"}},
        ]
        QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
        if PERF.exists():
            PERF.unlink()

        # 1. uploaded + video_id 항목만 대장에 등록 (pending 제외)
        added = analytics.sync_from_queue()
        assert added == 2, f"등록 수 오류: {added}"
        ids = {v["video_id"] for v in analytics._load()["videos"]}
        assert ids == {"VID1", "VID2"}, f"pending이 섞임: {ids}"

        # 2. 가짜 fetcher로 스냅샷 — 숨긴 지표(None)는 그대로 None
        fake1 = lambda vids: {"VID1": {"views": 100, "likes": 5, "comments": None},
                              "VID2": {"views": 10, "likes": None, "comments": 0}}
        r = analytics.snapshot(fetcher=fake1)
        assert r["updated"] == 2
        v1 = analytics._load()["videos"][0]["snapshots"][-1]
        assert v1["comments"] is None, "None을 지어냄!"

        # 3. 두 번째 스냅샷 → Δ 계산 정확 (100→130 = +30)
        fake2 = lambda vids: {"VID1": {"views": 130, "likes": 6, "comments": 1},
                              "VID2": {"views": 10, "likes": 0, "comments": 0}}
        analytics.snapshot(fetcher=fake2)
        s = analytics.summary()
        row = next(x for x in s["videos"] if "A" in x["title"])
        assert row["views_delta"] == 30, f"Δ 오류: {row['views_delta']}"
        assert row["snapshots"] == 2

        # 4. API 응답에서 빠진 영상 → 스냅샷 미추가 + note로 정직하게 보고
        r = analytics.snapshot(fetcher=lambda vids: {"VID1": {"views": 131, "likes": 6, "comments": 1}})
        assert r["updated"] == 1 and "VID2" in r.get("note", ""), r

        # 5. 스코어보드: 채택작 품질 평균 (대본 (90+70)/2=80 → Writer AI)
        board = analytics.update_scoreboard()
        writer = next(a for a in board["agents"] if a["name"] == "Writer AI")
        assert writer["score"] == 80.0, f"Writer 평균 오류: {writer['score']}"
        assert "규칙 기반" in writer["status"], "품질 예측치임을 명시해야 함"
        video_ai = next(a for a in board["agents"] if a["name"] == "Video AI")
        assert video_ai["score"] == 80.0  # (70+90)/2

        # 6. 업로드 영상 없음 → 오류가 아니라 안내
        q["items"] = []
        QUEUE.write_text(json.dumps(q, ensure_ascii=False), encoding="utf-8")
        PERF.unlink()
        r = analytics.snapshot(fetcher=lambda v: {})
        assert r["ok"] and r["updated"] == 0 and "업로드된 영상이 없습니다" in r["note"]

        print("✅ 성과 분석 테스트 6/6 통과")
    finally:
        for p, b in backups.items():
            if b is None:
                if p.exists():
                    p.unlink()
            else:
                p.write_text(b, encoding="utf-8")


if __name__ == "__main__":
    main()

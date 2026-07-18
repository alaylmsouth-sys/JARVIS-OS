"""video/analytics.py — 영상 성과 분석 (10단계 = t22).

★★ 원칙 ★★
  - 사실만 기록: API가 주지 않는 값은 None. 지어내지 않는다.
  - 직원별 성과 귀속 없음: 조회수는 영상 단위로만 표시한다.
  - 자동 갱신 없음: 사용자가 갱신을 실행할 때만 API를 호출한다.

사용:
  python3 -m video.analytics refresh    # 업로드된 전 영상 통계 1회 조회
  python3 -m video.analytics summary    # 저장된 성과 요약 출력
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MEMORY = ROOT / "memory"
PERF_FILE = MEMORY / "video_performance.json"
QUEUE_FILE = MEMORY / "approval_queue.json"
SCORE_FILE = MEMORY / "scoreboard.json"

# 품질 점수 역할 → 스코어보드 직원 매핑 (편집은 quality.py가 채점하지 않아 제외)
ROLE_MAP = {"대본": "Writer AI", "음성": "Voice AI", "영상": "Video AI"}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def _load() -> dict:
    if not PERF_FILE.exists():
        return {"note": "업로드된 영상의 실측 성과 스냅샷. [↻ 갱신] 시에만 API를 호출합니다.",
                "videos": []}
    return json.loads(PERF_FILE.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    PERF_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                         encoding="utf-8")


def sync_from_queue() -> int:
    """결재함에서 업로드 완료된 항목을 성과 대장에 등록. 새로 등록된 수 반환."""
    if not QUEUE_FILE.exists():
        return 0
    q = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    data = _load()
    known = {v["video_id"] for v in data["videos"]}
    added = 0
    for it in q.get("items", []):
        yt = it.get("youtube") or {}
        vid = yt.get("video_id")
        if it.get("status") == "uploaded" and vid and vid not in known:
            data["videos"].append({
                "item_id": it["id"], "video_id": vid,
                "title": it.get("title", "(제목 없음)"),
                "url": yt.get("url", f"https://youtu.be/{vid}"),
                "uploaded_at": yt.get("uploaded_at"),  # 과거 업로드분은 None일 수 있음
                "snapshots": [],
            })
            known.add(vid)
            added += 1
    if added:
        _save(data)
    return added


def _api_fetch(video_ids: list[str]) -> dict[str, dict]:
    """Data API v3 videos.list — {video_id: {views, likes, comments}}.
    값이 없거나 숨겨진 지표는 None."""
    import requests
    from security.youtube_auth import access_token
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "statistics", "id": ",".join(video_ids)},
        headers={"Authorization": f"Bearer {access_token()}"}, timeout=30)
    if r.status_code == 403:
        raise PermissionError(
            "유튜브 통계 조회 권한이 없습니다. 스코프가 추가되었으니 재인증하세요: "
            "python3 -m video.uploader auth")
    if r.status_code != 200:
        raise RuntimeError(f"통계 조회 실패 {r.status_code}: {r.text[:300]}")
    out: dict[str, dict] = {}
    for item in r.json().get("items", []):
        s = item.get("statistics", {})
        def _i(k):  # 유튜브가 숨긴 지표는 키 자체가 없음 → None
            return int(s[k]) if k in s else None
        out[item["id"]] = {"views": _i("viewCount"), "likes": _i("likeCount"),
                           "comments": _i("commentCount")}
    return out


def _api_fetch_watch(video_ids: list[str]) -> dict[str, dict]:
    """Analytics API v2 — {video_id: {watch_min, avg_view_sec}}.
    ⚠ CTR/노출수는 공개 API가 제공하지 않는다(Studio 전용) — 지어내지 않는다."""
    import requests
    from security.youtube_auth import access_token
    r = requests.get(
        "https://youtubeanalytics.googleapis.com/v2/reports",
        params={"ids": "channel==MINE", "startDate": "2020-01-01",
                "endDate": datetime.now().strftime("%Y-%m-%d"),
                "metrics": "estimatedMinutesWatched,averageViewDuration",
                "dimensions": "video",
                "filters": "video==" + ",".join(video_ids)},
        headers={"Authorization": f"Bearer {access_token()}"}, timeout=30)
    if r.status_code != 200:   # 스코프/미활성화 등 — 호출부에서 note로 처리
        raise RuntimeError(f"시청시간 조회 실패 {r.status_code}: {r.text[:200]}")
    out: dict[str, dict] = {}
    for row in r.json().get("rows", []) or []:
        out[row[0]] = {"watch_min": row[1], "avg_view_sec": row[2]}
    return out


def snapshot(fetcher=None, watch_fetcher=None) -> dict:
    """등록된 전 영상의 통계를 1회 조회해 스냅샷 추가.
    fetcher(video_ids)->dict 주입 가능 (테스트용, 기본은 실제 API).
    시청시간은 부가 정보 — 실패해도 기본 통계 스냅샷은 저장된다."""
    sync_from_queue()
    data = _load()
    if not data["videos"]:
        return {"ok": True, "updated": 0,
                "note": "업로드된 영상이 없습니다. 결재함에서 승인 → 업로드 후 다시 시도하세요."}
    ids = [v["video_id"] for v in data["videos"]]
    fetch = fetcher or _api_fetch
    stats = fetch(ids)
    watch, watch_note = {}, None
    try:
        watch = (watch_fetcher or _api_fetch_watch)(ids)
    except Exception as e:      # 시청시간은 없으면 없는 대로 — None으로 정직하게
        watch_note = f"시청시간 미조회 ({e})"
    at, updated, missing = _now(), 0, []
    for v in data["videos"]:
        got = stats.get(v["video_id"])
        if got is None:            # API 응답에 없음(삭제/비공개 등) — 사실대로 기록
            missing.append(v["video_id"])
            continue
        w = watch.get(v["video_id"], {})
        v["snapshots"].append({"at": at, **got,
                               "watch_min": w.get("watch_min"),
                               "avg_view_sec": w.get("avg_view_sec")})
        updated += 1
    _save(data)
    result = {"ok": True, "updated": updated, "at": at}
    notes = []
    if missing:
        notes.append(f"조회되지 않은 영상 {len(missing)}건 (삭제/권한 등): {missing}")
    if watch_note:
        notes.append(watch_note)
    if notes:
        result["note"] = " / ".join(notes)
    return result


def summary() -> dict:
    """영상별 최신 스냅샷 + 직전 대비 증감(Δ). 화면 표시용."""
    data = _load()
    rows = []
    for v in data["videos"]:
        snaps = v["snapshots"]
        latest = snaps[-1] if snaps else None
        prev = snaps[-2] if len(snaps) >= 2 else None
        delta = None
        if latest and prev and latest.get("views") is not None \
                and prev.get("views") is not None:
            delta = latest["views"] - prev["views"]
        rows.append({"title": v["title"], "url": v["url"],
                     "uploaded_at": v.get("uploaded_at"),
                     "latest": latest, "views_delta": delta,
                     "snapshots": len(snaps)})
    return {"note": data.get("note", ""), "videos": rows}


def update_scoreboard() -> dict:
    """채택작(업로드된 항목)의 품질 점수(규칙 기반) 역할별 평균을 기록.
    실측 성과가 아니라 채택작의 품질 예측치 평균 — status에 그대로 명시."""
    q = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    uploaded = [i for i in q.get("items", []) if i.get("status") == "uploaded"]
    board = json.loads(SCORE_FILE.read_text(encoding="utf-8"))
    if not uploaded:
        return board
    for role, agent_name in ROLE_MAP.items():
        vals = [i["quality"][role] for i in uploaded
                if isinstance(i.get("quality"), dict) and role in i["quality"]]
        if not vals:
            continue
        for a in board["agents"]:
            if a["name"] == agent_name:
                a["score"] = round(sum(vals) / len(vals), 1)
                a["status"] = f"채택작 {len(vals)}건 · 품질평균(규칙 기반)"
    board["note"] = ("score는 업로드가 승인·채택된 영상들의 품질 점수(규칙 기반) 평균입니다. "
                     "조회수 등 실측 성과는 '영상 성과' 섹션에 영상 단위로 표시합니다.")
    SCORE_FILE.write_text(json.dumps(board, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    return board


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refresh")
    sub.add_parser("summary")
    a = p.parse_args()
    if a.cmd == "refresh":
        r = snapshot()
        update_scoreboard()
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

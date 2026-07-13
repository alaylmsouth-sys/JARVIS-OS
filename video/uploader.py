"""video/uploader.py — 유튜브 업로드 (6단계 = t13).

★★ 핵심 원칙 ★★
  - CEO 결재함에서 status == "approved" 인 항목만 업로드할 수 있다.
  - 업로드는 사용자가 명시적으로 실행할 때만 (버튼/CLI). 자동 실행 없음.
  - 기본 공개 범위는 private(비공개) — 유튜브 스튜디오에서 확인 후 직접 공개 전환 권장.

사용:
  python3 -m video.uploader auth                 # 최초 1회 인증
  python3 -m video.uploader upload <결재ID>      # 승인된 항목 업로드
  python3 -m video.uploader upload <결재ID> --privacy unlisted
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from security.youtube_auth import access_token, authorize  # noqa: E402

MEMORY = ROOT / "memory"
QUEUE = MEMORY / "approval_queue.json"
OUTPUT = ROOT / "video" / "output"
PRIVACY_OPTIONS = ("private", "unlisted", "public")


def _queue() -> dict:
    return json.loads(QUEUE.read_text(encoding="utf-8"))


def _save_queue(q: dict) -> None:
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")


def upload(item_id: str, privacy: str = "private") -> dict:
    if privacy not in PRIVACY_OPTIONS:
        raise ValueError(f"privacy는 {PRIVACY_OPTIONS} 중 하나")
    q = _queue()
    item = next((i for i in q["items"] if i["id"] == item_id), None)
    if item is None:
        raise ValueError(f"결재 항목 없음: {item_id}")
    if item.get("status") != "approved":
        raise PermissionError(
            f"승인되지 않은 항목은 업로드할 수 없습니다 (현재: {item.get('status')}). "
            f"대시보드 CEO 결재함에서 먼저 승인하세요.")
    video_file = OUTPUT / item_id / "final.mp4"
    if not video_file.exists():
        raise FileNotFoundError(f"영상 파일 없음: {video_file}")

    scenes_file = OUTPUT / item_id / "scenes.json"
    description = ""
    if scenes_file.exists():
        description = json.loads(scenes_file.read_text(encoding="utf-8")).get("description", "")

    token = access_token()
    meta = {
        "snippet": {
            "title": item["title"][:100],
            "description": description[:4900],
            "tags": item.get("tags", [])[:15],
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }

    # 1) 재개형 업로드 세션 시작
    size = video_file.stat().st_size
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4",
                 "X-Upload-Content-Length": str(size)},
        json=meta, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"업로드 세션 실패 {r.status_code}: {r.text[:400]}")
    session = r.headers["Location"]

    # 2) 영상 전송
    with open(video_file, "rb") as f:
        up = requests.put(session,
                          headers={"Authorization": f"Bearer {token}",
                                   "Content-Type": "video/mp4"},
                          data=f, timeout=1800)
    if up.status_code not in (200, 201):
        raise RuntimeError(f"업로드 실패 {up.status_code}: {up.text[:400]}")
    video_id = up.json()["id"]
    url = f"https://youtu.be/{video_id}"

    # 3) 결재함 기록 갱신
    from datetime import datetime, timezone
    item["status"] = "uploaded"
    item["youtube"] = {"video_id": video_id, "url": url, "privacy": privacy,
                       "uploaded_at": datetime.now(timezone.utc)
                       .astimezone().strftime("%Y-%m-%d %H:%M")}
    _save_queue(q)

    # 4) AI PM 연동: 첫 업로드 성공 → t13 완료
    from brain import project_manager as pm
    state = pm.load_state()
    for phase in state["phases"]:
        for t in phase["tasks"]:
            if t["id"] == "t13" and not t["done"]:
                t["done"] = True
                pm.save_state(state)

    return {"video_id": video_id, "url": url, "privacy": privacy}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    u = sub.add_parser("upload")
    u.add_argument("item_id")
    u.add_argument("--privacy", default="private", choices=PRIVACY_OPTIONS)
    a = p.parse_args()
    if a.cmd == "auth":
        authorize()
    else:
        r = upload(a.item_id, a.privacy)
        print(f"✅ 업로드 완료 ({r['privacy']}): {r['url']}")
        print("유튜브 스튜디오에서 확인 후 공개 전환을 권장합니다.")


if __name__ == "__main__":
    main()

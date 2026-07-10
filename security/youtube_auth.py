"""security/youtube_auth.py — 유튜브 OAuth (기기 코드 방식).

리디렉션 서버가 필요 없는 'TV 및 제한된 입력 기기' OAuth 흐름을 사용한다.
터미널에 표시되는 코드를 google.com/device 에 입력하면 인증 완료.

필요 설정 (.env):
  YT_CLIENT_ID=...       (Google Cloud 콘솔에서 발급)
  YT_CLIENT_SECRET=...

토큰 저장: memory/youtube_token.json (★.gitignore 필수 — 계정 접근 권한임)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from security.keys import get_key  # noqa: E402

TOKEN_FILE = ROOT / "memory" / "youtube_token.json"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def _client() -> tuple[str, str]:
    cid, csec = get_key("YT_CLIENT_ID"), get_key("YT_CLIENT_SECRET")
    if not cid or not csec:
        raise RuntimeError(
            ".env에 YT_CLIENT_ID, YT_CLIENT_SECRET이 필요합니다. "
            "발급 방법은 docs/08-phase6-upload.md 참고.")
    return cid, csec


def authorize() -> None:
    """기기 코드 흐름으로 최초 인증. 대화형(터미널)으로 실행."""
    cid, csec = _client()
    r = requests.post("https://oauth2.googleapis.com/device/code",
                      data={"client_id": cid, "scope": SCOPE}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"기기 코드 발급 실패 {r.status_code}: {r.text[:300]}")
    d = r.json()
    print("─" * 50)
    print(f"1. 브라우저에서 열기:  {d['verification_url']}")
    print(f"2. 코드 입력:          {d['user_code']}")
    print("─" * 50)
    print("인증을 기다리는 중… (완료하면 자동 진행)")

    interval = d.get("interval", 5)
    for _ in range(int(d["expires_in"] / interval)):
        time.sleep(interval)
        t = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": cid, "client_secret": csec,
            "device_code": d["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }, timeout=30)
        body = t.json()
        if t.status_code == 200:
            TOKEN_FILE.write_text(json.dumps(body, indent=2), encoding="utf-8")
            print("✅ 인증 완료 — 토큰이 memory/youtube_token.json에 저장되었습니다.")
            return
        if body.get("error") == "authorization_pending":
            continue
        if body.get("error") == "slow_down":
            interval += 2
            continue
        raise RuntimeError(f"인증 실패: {body}")
    raise TimeoutError("인증 시간 초과 — 다시 실행하세요.")


def access_token() -> str:
    """저장된 refresh_token으로 액세스 토큰 갱신."""
    if not TOKEN_FILE.exists():
        raise RuntimeError("유튜브 인증이 필요합니다: python3 -m video.uploader auth")
    tok = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    refresh = tok.get("refresh_token")
    if not refresh:
        raise RuntimeError("refresh_token 없음 — 인증을 다시 실행하세요.")
    cid, csec = _client()
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": cid, "client_secret": csec,
        "refresh_token": refresh, "grant_type": "refresh_token",
    }, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"토큰 갱신 실패 {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]

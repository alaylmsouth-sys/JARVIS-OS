"""security/health.py — 시스템센터 자가 점검 (13단계 = t35).

환경/데이터/백업 상태를 점검해 ✅/⚠/❌ 목록으로 보여준다.

★★ 원칙 ★★
  - 점검은 읽기만 한다 — 아무것도 고치거나 지우지 않는다.
  - 외부 네트워크 호출 없음 (전부 로컬 확인).

사용:  python3 -m security.health
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from security.keys import has_key  # noqa: E402

MEMORY = ROOT / "memory"
DATA_DIR = Path(os.environ.get("JARVIS_DATA_DIR", Path.home() / ".jarvis-data"))

OK, WARN, FAIL = "ok", "warn", "fail"


def _c(name: str, level: str, detail: str) -> dict:
    return {"name": name, "level": level, "detail": detail}


def run_checks() -> list[dict]:
    checks: list[dict] = []

    # 1. 실행 환경
    v = sys.version_info
    checks.append(_c("Python", OK if v >= (3, 10) else FAIL, f"{v.major}.{v.minor}"))
    checks.append(_c("FFmpeg (영상 제작)", OK if shutil.which("ffmpeg") else FAIL,
                     "설치됨" if shutil.which("ffmpeg") else "없음 — 영상 파이프라인 불가"))

    # 2. 키/인증 (값은 절대 표시하지 않음)
    for label, key in [("Gemini 키", "GEMINI_API_KEY"),
                       ("유튜브 클라이언트", "YT_CLIENT_ID")]:
        ok = has_key(key)
        checks.append(_c(label, OK if ok else WARN,
                         "설정됨" if ok else f"{key} 미설정"))
    token = MEMORY / "youtube_token.json"
    if token.exists():
        try:
            scope = json.loads(token.read_text(encoding="utf-8")).get("scope", "")
            good = "youtube.readonly" in scope
            checks.append(_c("유튜브 인증", OK if good else WARN,
                             "업로드+통계 권한" if good else
                             "구버전 토큰(업로드만) — 통계 조회엔 재인증 필요"))
        except Exception:
            checks.append(_c("유튜브 인증", WARN, "토큰 파일 손상 — 재인증 필요"))
    else:
        checks.append(_c("유튜브 인증", WARN, "미인증 — 업로드/통계 사용 시 auth 실행"))

    # 3. memory 무결성 (전 JSON 파싱)
    broken = []
    for f in sorted(MEMORY.glob("*.json")):
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            broken.append(f.name)
    checks.append(_c("memory 무결성",
                     FAIL if broken else OK,
                     f"손상: {broken} — 백업에서 복원 권장" if broken
                     else f"{len(list(MEMORY.glob('*.json')))}개 파일 정상"))

    # 4. 백업 상태 (비공개 데이터 저장소)
    if not (DATA_DIR / ".git").exists():
        checks.append(_c("백업 (JARVIS-DATA)", WARN,
                         "연결 안 됨 — ./backup.sh 최초 실행 필요"))
    else:
        # 4a. 마지막 백업 시각
        try:
            t = subprocess.run(["git", "-C", str(DATA_DIR), "log", "-1",
                                "--format=%ci"], capture_output=True, text=True,
                               timeout=10).stdout.strip()[:16]
            # 로컬 memory가 백업 이후에 바뀌었는지
            last_backup = datetime.fromisoformat(t) if t else None
            newest_local = max((f.stat().st_mtime for f in MEMORY.glob("*.json")),
                               default=0)
            stale = last_backup and newest_local > last_backup.timestamp()
            checks.append(_c("백업 (JARVIS-DATA)", WARN if stale else OK,
                             f"마지막 백업 {t}" + (" — 이후 변경 있음, ./backup.sh 권장"
                                               if stale else "")))
        except Exception as e:
            checks.append(_c("백업 (JARVIS-DATA)", WARN, f"확인 실패: {e}"))
        # 4b. 데이터 저장소 오염 검사 — 코드 폴더가 섞여 있으면 경고
        polluted = [d for d in ("dashboard", "video", "router", "agents", "docs")
                    if (DATA_DIR / d).exists()]
        if polluted:
            checks.append(_c("데이터 저장소 구성", WARN,
                             f"코드 폴더가 섞여 있음 {polluted} — 데이터 전용 저장소 권장 "
                             "(docs/13 참고: 빈 Private 저장소로 재생성)"))
        else:
            checks.append(_c("데이터 저장소 구성", OK, "memory 데이터만 존재 (깨끗함)"))

    # 5. 디스크 (영상 산출물)
    out = ROOT / "video" / "output"
    size_mb = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1e6 \
        if out.exists() else 0
    checks.append(_c("영상 산출물 용량", WARN if size_mb > 500 else OK,
                     f"{size_mb:.0f} MB" + (" — 정리 권장" if size_mb > 500 else "")))

    return checks


def main() -> None:
    icons = {OK: "✅", WARN: "⚠", FAIL: "❌"}
    for c in run_checks():
        print(f"{icons[c['level']]} {c['name']}: {c['detail']}")


if __name__ == "__main__":
    main()

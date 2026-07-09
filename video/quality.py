"""video/quality.py — Quality Inspector v1 (규칙 기반).

⚠ 정직성 원칙: 이 점수는 파일/길이/형식 등 확인 가능한 항목의
규칙 기반 점수다. "예상 클릭률" 같은 예측은 근거 데이터가 쌓이기
전까지 제공하지 않는다 (Memory 2.0에 성과 데이터가 쌓이면 추가).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _probe(video: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(video)],
        capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def inspect(video: Path, thumb: Path, scenes: dict, script: str) -> dict:
    warnings: list[str] = []
    scores: dict[str, int] = {}

    # ── 영상 검사 ──
    v = 100
    info = _probe(video)
    duration = float(info["format"]["duration"])
    target = sum(s["seconds"] for s in scenes["scenes"])
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = stream["width"], stream["height"]
    if abs(duration - target) > 2:
        v -= 20; warnings.append(f"영상 길이 {duration:.1f}s가 목표 {target}s와 다름")
    if (w, h) != (1080, 1920):
        v -= 15; warnings.append(f"해상도 {w}x{h} (쇼츠 권장 1080x1920)")
    if not (15 <= duration <= 60):
        v -= 15; warnings.append(f"쇼츠 길이 범위(15~60초) 벗어남: {duration:.0f}초")
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    if not has_audio:
        v -= 30; warnings.append("오디오 트랙 없음")
    scores["영상"] = max(v, 0)

    # ── 대본 검사 ──
    d = 100
    title = scenes.get("title", "")
    if not title:
        d -= 30; warnings.append("제목 없음")
    elif len(title) > 45:
        d -= 10; warnings.append(f"제목이 김 ({len(title)}자, 45자 이하 권장)")
    if not scenes.get("hook"):
        d -= 20; warnings.append("훅(첫 3초 문장) 없음")
    for s in scenes["scenes"]:
        rate = len(s["narration"]) / max(s["seconds"], 1)
        if rate > 8:
            d -= 5
            warnings.append(f"장면{s['n']} 나레이션이 빠름 ({rate:.1f}자/초, 8자/초 이하 권장)")
    scores["대본"] = max(d, 0)

    # ── 음성 검사 ──
    a = 100
    astream = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if astream is None:
        a = 0
    else:
        # 무음 여부 (silent provider 감지)
        vol = subprocess.run(
            ["ffmpeg", "-i", str(video), "-af", "volumedetect",
             "-f", "null", "-"], capture_output=True, text=True)
        if "mean_volume: -91" in vol.stderr or "mean_volume: -inf" in vol.stderr:
            a = 40; warnings.append("음성이 무음입니다 (TTS 미연결 상태)")
    scores["음성"] = a

    # ── 썸네일 검사 ──
    t = 100
    if not thumb.exists() or thumb.stat().st_size < 5000:
        t = 20; warnings.append("썸네일 생성 실패 또는 비정상")
    scores["썸네일"] = t

    avg = sum(scores.values()) / len(scores)
    if avg >= 85 and not warnings:
        rec = "업로드 검토 가능 (규칙 기반 점수이며 성과를 보장하지 않음)"
    elif avg >= 60:
        rec = "수정 권장 — 경고 항목 확인 후 결정하세요"
    else:
        rec = "재생성 권장 — 주요 문제가 발견됨"

    return {"scores": scores, "warnings": warnings, "recommendation": rec}

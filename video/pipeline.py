"""video/pipeline.py — 영상 자동 제작 파이프라인 (3단계).

주제 → 대본 → 장면 분할 → 장면별 영상 → 음성 → 편집(자막) → 썸네일
→ 품질 검사 → CEO 결재함 등록.  ★ 업로드는 절대 하지 않는다 — 승인 대기까지만.

사용:
  python -m video.pipeline "주제" --dry-run     # AI 호출 없이 전체 구조 테스트
  python -m video.pipeline "주제"               # 대본/장면은 실제 AI, 영상은 설정된 provider
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain.bootstrap import ensure_memory  # noqa: E402
from router.router import route, load_table  # noqa: E402
from video import videogen, voice, editor, thumbnail, quality  # noqa: E402

MEMORY = ROOT / "memory"
OUTPUT = ROOT / "video" / "output"

_SAMPLE_SCENES = {
    "title": "AI가 세상을 바꾸는 3가지 방법",
    "hook": "이 사실, 아직 모르는 사람이 90%입니다.",
    "scenes": [
        {"n": 1, "narration": "인공지능이 이미 우리 일상에 들어와 있습니다.", "visual": "futuristic city with holographic AI interfaces", "seconds": 6},
        {"n": 2, "narration": "첫째, 영상 하나를 만드는 시간이 하루에서 십 분으로 줄었습니다.", "visual": "timelapse of video editing workstation", "seconds": 7},
        {"n": 3, "narration": "둘째, 개인도 AI 직원을 고용하는 시대가 왔습니다.", "visual": "person working with multiple AI assistant screens", "seconds": 7},
        {"n": 4, "narration": "셋째, 중요한 결정은 여전히 사람이 내립니다.", "visual": "human hand pressing approval button on futuristic dashboard", "seconds": 6},
    ],
    "outro": "다음 이야기가 궁금하다면 구독을 눌러주세요.",
    "tags": ["AI", "자동화", "쇼츠"],
    "description": "AI가 바꾸는 일상 3가지를 소개합니다.",
}


def _parse_scenes(text: str) -> dict:
    """AI 응답에서 JSON 추출 (백틱 포함 대비)."""
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("장면 JSON을 찾지 못했습니다:\n" + text[:300])
    return json.loads(text[start:end + 1])


def run(topic: str, dry_run: bool = False) -> dict:
    # CLI와 자동화에서 대시보드를 거치지 않아도 안전하게 초기 설정을 준비한다.
    ensure_memory()
    job_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    job_dir = OUTPUT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    table = load_table()
    log = lambda msg: print(f"  [{job_id}] {msg}")  # noqa: E731

    log(f"주제: {topic}" + (" (dry-run)" if dry_run else ""))

    # 1) 대본
    log("1/7 대본 생성 (Writer AI)…")
    script = route("script", topic, dry_run=dry_run)["result"]["text"]
    (job_dir / "script.txt").write_text(script, encoding="utf-8")

    # 2) 장면 분할
    log("2/7 장면 분할…")
    if dry_run:
        scenes = json.loads(json.dumps(_SAMPLE_SCENES, ensure_ascii=False))
        scenes["title"] = f"[테스트] {topic}"
    else:
        raw = route("scenes", f"다음 대본을 장면으로 분할:\n\n{script}")["result"]["text"]
        scenes = _parse_scenes(raw)
    (job_dir / "scenes.json").write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3) 장면별 영상 생성
    vconf = table["media"]["video"]
    # dry-run은 구성값과 관계없이 네트워크·유료 생성 서비스를 호출하지 않는다.
    if dry_run:
        vconf = {**vconf, "provider": "placeholder"}
    log(f"3/7 영상 생성 ({vconf['provider']})…")
    clips = videogen.generate_clips(scenes["scenes"], vconf, job_dir)

    # 4) 음성 생성
    aconf = table["media"]["voice"]
    if dry_run:
        aconf = {**aconf, "provider": "silent"}
    log(f"4/7 음성 생성 ({aconf['provider']})…")
    narration = " ".join([scenes["hook"]] +
                         [s["narration"] for s in scenes["scenes"]] +
                         [scenes["outro"]])
    total_sec = sum(s["seconds"] for s in scenes["scenes"])
    audio = voice.generate(narration, total_sec, aconf, job_dir)

    # 5) 편집 (합치기 + 자막)
    log("5/7 편집 (FFmpeg)…")
    final = editor.assemble(clips, audio, scenes, job_dir)

    # 6) 썸네일
    log("6/7 썸네일…")
    thumb = thumbnail.create(final, scenes["title"], job_dir)

    # 7) 품질 검사 → 결재함 등록
    log("7/7 품질 검사 (Quality Inspector)…")
    report = quality.inspect(final, thumb, scenes, script)

    item = {
        "id": job_id,
        "type": "video",
        "title": scenes["title"],
        "length": f"{total_sec // 60:02d}:{total_sec % 60:02d}",
        "tags": scenes.get("tags", []),
        "quality": report["scores"],
        "recommendation": report["recommendation"],
        "warnings": report["warnings"],
        "files": {
            "video": f"/media/{job_id}/final.mp4",
            "thumbnail": f"/media/{job_id}/thumbnail.jpg",
            "script": f"/media/{job_id}/script.txt",
        },
        "status": "pending",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dry_run": dry_run,
    }
    qfile = MEMORY / "approval_queue.json"
    q = json.load(open(qfile, encoding="utf-8"))
    q["items"].insert(0, item)
    json.dump(q, open(qfile, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    log(f"완료 → CEO 결재함에 등록됨. 대시보드에서 검토하세요.")
    log(f"영상: {final}")
    return item


def main():
    p = argparse.ArgumentParser()
    p.add_argument("topic")
    p.add_argument("--dry-run", action="store_true",
                   help="AI 호출 없이 전체 구조 테스트 (placeholder 영상)")
    a = p.parse_args()
    run(a.topic, dry_run=a.dry_run)


if __name__ == "__main__":
    main()

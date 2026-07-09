"""video/videogen.py — 장면별 영상 클립 생성.

provider:
  placeholder — FFmpeg로 로컬 생성 (무료). 장면 묘사 텍스트가 화면에 표시된다.
  gemini_veo  — Google Veo 3.1 (Gemini API). GEMINI_API_KEY 필요.
  fal_kling   — Kling 3.0 (fal.ai 경유). FAL_KEY 필요.

⚠ gemini_veo / fal_kling 어댑터는 공식 문서 기준으로 작성했으나
  실제 키로 검증되지 않았다 (docs/05 참고). 첫 실행 시 오류가 나면
  응답 형식을 확인해 조정이 필요할 수 있다.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from security.keys import get_key  # noqa: E402

PALETTE = ["0x1a2744", "0x24344f", "0x1f3a4a", "0x2a2f4a", "0x203548",
           "0x2e2a45", "0x1c3040"]


def _placeholder_clip(scene: dict, out: Path, resolution: str) -> None:
    """FFmpeg로 장면 카드 영상 생성 (그라데이션 배경 + 장면 번호/묘사)."""
    w, h = resolution.split("x")
    color = PALETTE[(scene["n"] - 1) % len(PALETTE)]
    textfile = out.with_suffix(".txt")
    textfile.write_text(f"장면 {scene['n']}\n\n{scene['visual']}", encoding="utf-8")
    font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    if not Path(font).exists():
        font = ""  # 폰트 없으면 텍스트 생략
    draw = (f",drawtext=textfile='{textfile}':fontfile='{font}':fontsize=42:"
            f"fontcolor=white@0.85:x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=16"
            if font else "")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i",
         f"color=c={color}:s={w}x{h}:d={scene['seconds']}:r=30",
         "-vf", f"format=yuv420p{draw}",
         "-c:v", "libx264", "-preset", "fast", str(out)],
        check=True,
    )
    textfile.unlink(missing_ok=True)


def _veo_clip(scene: dict, conf: dict, out: Path) -> None:
    """Google Veo (Gemini API, 비동기 long-running operation)."""
    key = get_key(conf["env_key"])
    if not key:
        raise RuntimeError(f".env에 {conf['env_key']}가 필요합니다.")
    model = conf["model"]
    base = "https://generativelanguage.googleapis.com/v1beta"
    r = requests.post(
        f"{base}/models/{model}:predictLongRunning",
        params={"key": key},
        json={"instances": [{"prompt": scene["visual"]}],
              "parameters": {"aspectRatio": "9:16"}},
        timeout=60,
    )
    r.raise_for_status()
    op = r.json()["name"]
    for _ in range(60):  # 최대 10분 대기
        time.sleep(10)
        s = requests.get(f"{base}/{op}", params={"key": key}, timeout=30)
        s.raise_for_status()
        d = s.json()
        if d.get("done"):
            uri = d["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
            video = requests.get(uri, params={"key": key}, timeout=300)
            out.write_bytes(video.content)
            return
    raise TimeoutError("Veo 영상 생성 시간 초과")


def _kling_clip(scene: dict, conf: dict, out: Path) -> None:
    """Kling (fal.ai queue API)."""
    key = get_key(conf["env_key"])
    if not key:
        raise RuntimeError(f".env에 {conf['env_key']}가 필요합니다.")
    model = conf["model"]
    r = requests.post(
        f"https://queue.fal.run/{model}",
        headers={"Authorization": f"Key {key}"},
        json={"prompt": scene["visual"], "duration": str(scene["seconds"]),
              "aspect_ratio": "9:16"},
        timeout=60,
    )
    r.raise_for_status()
    req = r.json()
    status_url, response_url = req["status_url"], req["response_url"]
    for _ in range(60):
        time.sleep(10)
        s = requests.get(status_url, headers={"Authorization": f"Key {key}"},
                         timeout=30).json()
        if s.get("status") == "COMPLETED":
            d = requests.get(response_url,
                             headers={"Authorization": f"Key {key}"},
                             timeout=30).json()
            url = d["video"]["url"]
            out.write_bytes(requests.get(url, timeout=300).content)
            return
    raise TimeoutError("Kling 영상 생성 시간 초과")


def generate_clips(scenes: list[dict], vconf: dict, job_dir: Path) -> list[Path]:
    provider = vconf["provider"]
    resolution = vconf.get("resolution", "1080x1920")
    clips = []
    for scene in scenes:
        out = job_dir / f"scene_{scene['n']:02d}.mp4"
        if provider == "placeholder":
            _placeholder_clip(scene, out, resolution)
        elif provider == "gemini_veo":
            _veo_clip(scene, vconf["providers"]["gemini_veo"], out)
        elif provider == "fal_kling":
            _kling_clip(scene, vconf["providers"]["fal_kling"], out)
        else:
            raise ValueError(f"알 수 없는 영상 provider: {provider}")
        clips.append(out)
    return clips

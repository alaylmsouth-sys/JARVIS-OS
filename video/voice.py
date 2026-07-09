"""video/voice.py — 나레이션 음성 생성.
provider: silent(무음, 테스트) / elevenlabs(한국어 TTS, ELEVENLABS_API_KEY + voice_id 필요)
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from security.keys import get_key  # noqa: E402


def generate(text: str, total_seconds: int, aconf: dict, job_dir: Path) -> Path:
    provider = aconf["provider"]
    if provider == "silent":
        out = job_dir / "narration.m4a"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
             "-i", f"anullsrc=r=44100:cl=stereo:d={total_seconds}",
             "-c:a", "aac", str(out)], check=True)
        return out
    if provider == "elevenlabs":
        conf = aconf["providers"]["elevenlabs"]
        key = get_key(conf["env_key"])
        if not key:
            raise RuntimeError(f".env에 {conf['env_key']}가 필요합니다.")
        if not conf.get("voice_id"):
            raise RuntimeError("routing_table.json의 media.voice.providers.elevenlabs.voice_id를 입력하세요.")
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{conf['voice_id']}",
            headers={"xi-api-key": key, "content-type": "application/json"},
            json={"text": text, "model_id": conf.get("model", "eleven_multilingual_v2")},
            timeout=300)
        r.raise_for_status()
        out = job_dir / "narration.mp3"
        out.write_bytes(r.content)
        return out
    raise ValueError(f"알 수 없는 음성 provider: {provider}")

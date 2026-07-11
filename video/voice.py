"""video/voice.py — 나레이션 음성 생성.

provider:
  silent      — 무음 트랙 (테스트용)
  gemini_tts  — Gemini TTS (기존 GEMINI_API_KEY 재사용, 추가 비용 없이 무료 한도 사용)
  elevenlabs  — ElevenLabs 한국어 TTS (ELEVENLABS_API_KEY + voice_id 필요)

gemini_tts는 PCM(원시 오디오)을 반환하므로 WAV로 감싸 저장한다.
첫 실제 TTS 성공 시 t11을 자동 완료 처리한다 (AI PM 연동).
"""

from __future__ import annotations

import base64
import struct
import sys
import wave
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from security.keys import get_key  # noqa: E402

TIMEOUT = 300

# 모델 은퇴 대비 예비 후보 (Watchdog 방식)
GEMINI_TTS_MODELS = [
    "gemini-2.5-flash-preview-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-pro-preview-tts",
]


def pcm_to_wav(pcm: bytes, out: Path, rate: int = 24000) -> Path:
    """16비트 모노 PCM → WAV 파일."""
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out


def _parse_rate(mime: str) -> int:
    """예: 'audio/L16;codec=pcm;rate=24000' → 24000"""
    for part in mime.split(";"):
        if part.strip().startswith("rate="):
            try:
                return int(part.split("=")[1])
            except ValueError:
                pass
    return 24000


def _gemini_tts(text: str, conf: dict, job_dir: Path) -> Path:
    key = get_key(conf.get("env_key", "GEMINI_API_KEY"))
    if not key:
        raise RuntimeError(".env에 GEMINI_API_KEY가 필요합니다.")
    voice = conf.get("voice", "Kore")
    models = [conf["model"]] if conf.get("model") else []
    models += [m for m in GEMINI_TTS_MODELS if m not in models]

    last = None
    for model in models:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key},
            json={
                "contents": [{"parts": [{"text": text}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {"voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice}}},
                },
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            part = r.json()["candidates"][0]["content"]["parts"][0]
            blob = part.get("inlineData") or part.get("inline_data")
            if not blob:
                raise RuntimeError(f"TTS 응답에 오디오 없음: {str(part)[:200]}")
            pcm = base64.b64decode(blob["data"])
            rate = _parse_rate(blob.get("mimeType") or blob.get("mime_type", ""))
            out = pcm_to_wav(pcm, job_dir / "narration.wav", rate)
            if model != (conf.get("model") or model):
                print(f"⚠ Watchdog: TTS 모델 {conf.get('model')} 사용 불가 → {model}(으)로 자동 전환")
            _mark_t11_done()
            return out
        last = f"{model} → {r.status_code}: {r.text[:200]}"
        if r.status_code not in (404, 429, 503):
            break
    raise RuntimeError(f"gemini TTS 실패 (모든 후보): {last}")


def _mark_t11_done() -> None:
    try:
        from brain import project_manager as pm
        state = pm.load_state()
        for phase in state["phases"]:
            for t in phase["tasks"]:
                if t["id"] == "t11" and not t["done"]:
                    t["done"] = True
                    pm.save_state(state)
    except Exception:
        pass  # 진행률 갱신 실패가 TTS를 막으면 안 됨


def generate(text: str, total_seconds: int, aconf: dict, job_dir: Path) -> Path:
    provider = aconf["provider"]

    if provider == "silent":
        import subprocess
        out = job_dir / "narration.m4a"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
             "-i", f"anullsrc=r=44100:cl=stereo:d={total_seconds}",
             "-c:a", "aac", str(out)], check=True)
        return out

    if provider == "gemini_tts":
        return _gemini_tts(text, aconf["providers"]["gemini_tts"], job_dir)

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
            timeout=TIMEOUT)
        if r.status_code >= 400:
            raise RuntimeError(f"elevenlabs 오류 {r.status_code}: {r.text[:300]}")
        out = job_dir / "narration.mp3"
        out.write_bytes(r.content)
        return out

    raise ValueError(f"알 수 없는 음성 provider: {provider}")

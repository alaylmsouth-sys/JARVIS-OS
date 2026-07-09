"""agents/writer.py — 텍스트 생성 AI 직원 어댑터.

세 가지 provider(anthropic / openai / gemini)를 같은 인터페이스로 호출한다.
반환 형식은 항상 동일:
    {"text": str, "input_tokens": int, "output_tokens": int, "model": str}

dry_run=True 이면 API를 호출하지 않고 가짜 응답을 돌려준다 (테스트/키 없이 구조 확인용).
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from security.keys import get_key  # noqa: E402

TIMEOUT = 120


class MissingKeyError(RuntimeError):
    pass


def generate(provider: str, model: str, system: str, prompt: str,
             env_key: str, dry_run: bool = False, max_tokens: int = 2000) -> dict:
    if dry_run:
        return {
            "text": f"[DRY-RUN] provider={provider}, model={model}\n"
                    f"제목: (예시) {prompt[:20]}… 에 대한 쇼츠\n"
                    f"훅: 이 사실, 알고 계셨나요?\n장면1: …\n장면2: …\n"
                    f"마무리: 더 알고 싶다면 구독!",
            "input_tokens": 120, "output_tokens": 240, "model": model,
        }

    key = get_key(env_key)
    if not key:
        raise MissingKeyError(
            f"{provider} API 키가 없습니다. 프로젝트 루트의 .env 파일에 "
            f"{env_key}=... 형식으로 추가하세요. (.env.example 참고)"
        )

    if provider == "anthropic":
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": model, "max_tokens": max_tokens, "system": system,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=TIMEOUT,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"{provider} API 오류 {r.status_code}: {r.text[:500]}")
        d = r.json()
        text = "".join(b.get("text", "") for b in d.get("content", []))
        u = d.get("usage", {})
        return {"text": text, "input_tokens": u.get("input_tokens", 0),
                "output_tokens": u.get("output_tokens", 0), "model": d.get("model", model)}

    if provider == "openai":
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
            json={"model": model, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": prompt}]},
            timeout=TIMEOUT,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"{provider} API 오류 {r.status_code}: {r.text[:500]}")
        d = r.json()
        u = d.get("usage", {})
        return {"text": d["choices"][0]["message"]["content"],
                "input_tokens": u.get("prompt_tokens", 0),
                "output_tokens": u.get("completion_tokens", 0),
                "model": d.get("model", model)}

    if provider == "gemini":
        # Watchdog v0: 모델 은퇴/차단(404, 429 limit:0) 시 예비 후보로 자동 재시도
        fallbacks = [model, "gemini-3-flash-preview", "gemini-flash-latest",
                     "gemini-flash-lite-latest", "gemini-3.1-flash-lite"]
        last_err = None
        for m in dict.fromkeys(fallbacks):
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                headers={"x-goog-api-key": key},
                json={"system_instruction": {"parts": [{"text": system}]},
                      "contents": [{"parts": [{"text": prompt}]}]},
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                if m != model:
                    print(f"⚠ Watchdog: {model} 사용 불가 → {m}(으)로 자동 전환됨. "
                          f"routing_table.json 갱신을 권장합니다.")
                d = r.json()
                text = "".join(pt.get("text", "")
                               for pt in d["candidates"][0]["content"].get("parts", []))
                u = d.get("usageMetadata", {})
                return {"text": text, "input_tokens": u.get("promptTokenCount", 0),
                        "output_tokens": u.get("candidatesTokenCount", 0), "model": m}
            last_err = f"{r.status_code}: {r.text[:300]}"
            if r.status_code not in (404, 429, 503):
                break
        raise RuntimeError(f"gemini API 오류 (모든 후보 실패) {last_err}")

    if provider == "_gemini_old_disabled":
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key},
            json={"system_instruction": {"parts": [{"text": system}]},
                  "contents": [{"parts": [{"text": prompt}]}]},
            timeout=TIMEOUT,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"{provider} API 오류 {r.status_code}: {r.text[:500]}")
        d = r.json()
        text = "".join(p.get("text", "")
                       for p in d["candidates"][0]["content"].get("parts", []))
        u = d.get("usageMetadata", {})
        return {"text": text, "input_tokens": u.get("promptTokenCount", 0),
                "output_tokens": u.get("candidatesTokenCount", 0), "model": model}

    raise ValueError(f"알 수 없는 provider: {provider}")

# 7단계 · 음성 TTS (v0.7.0, t11)

## 결정: Gemini TTS 우선

사용자의 GEMINI_API_KEY 하나로 대본·장면분할에 이어 **나레이션까지** 해결.
추가 가입/비용 없이 무료 한도로 시작 (ElevenLabs 어댑터는 유지 — 목소리
품질을 올리고 싶을 때 교체 옵션).

- 예비 모델 자동 전환(Watchdog 방식): 2.5-flash-preview-tts → 3.1-flash-tts-preview → 2.5-pro-preview-tts
- 목소리: prebuilt voice (기본 Kore, routing_table의 media.voice.providers.gemini_tts.voice로 변경)
- 응답은 원시 PCM → WAV로 래핑 (wave 모듈, 테스트 검증)
- 첫 실제 TTS 성공 시 t11 자동 완료 (AI PM 연동)

## 편집기 개선

나레이션 길이가 영상과 다를 수 있어 `-af apad` 추가 — 나레이션이 짧으면
무음 패딩으로 영상 길이 유지. (한계: 나레이션이 영상보다 길면 잘림.
장면별 TTS + 클립 길이 동기화는 후순위 개선 과제)

## 활성화 (사용자 실행)

```bash
python3 -c "
import json
p = 'memory/routing_table.json'
t = json.load(open(p, encoding='utf-8'))
t['media']['voice']['provider'] = 'gemini_tts'
t['media']['voice']['providers']['gemini_tts'] = {
    'env_key': 'GEMINI_API_KEY', 'model': 'gemini-2.5-flash-preview-tts',
    'voice': 'Kore', 'description': 'Gemini TTS (무료 한도)'}
json.dump(t, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('✅ 음성 provider = gemini_tts')
"
python3 -m video.pipeline "주제"   # 이제 목소리가 들어간 영상이 나옴
```

## 테스트

- [x] PCM→WAV 래퍼 정확성(24kHz/모노/1초), mime rate 파싱
- [x] silent 회귀 통과, 알 수 없는 provider 거부
- [x] 전체 파이프라인 회귀 4/4
- [ ] 실제 Gemini TTS 호출 (사용자 실행 — TTS 무료 한도는 텍스트보다 빡빡할 수 있음.
      429 시 잠시 후 재시도, 지속되면 오류 공유)

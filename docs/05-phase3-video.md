# 3단계 · 영상 자동 제작 (v0.3.0)

## 영상 AI 조사 결과 (2026-07-09 웹 검색 기준 — 가격/정책 변동 가능)

| 서비스 | 대략 가격 | 특징 | 접근 |
|---|---|---|---|
| Kling 3.0 | ~$0.10/초 | 가성비 최고, 캐릭터 일관성 | fal.ai 등 셀프서브 |
| Veo 3.1 Fast | ~$0.15/초 | **네이티브 오디오 포함**, 안정적 | Gemini API (지역 제한 있음) |
| Veo 3.1 Standard | ~$0.40/초 | 최고 품질, 4K | Gemini API / Vertex |
| Runway Gen-4.5 | ~$0.20/초 | 편집 제어 최강 | **엔터프라이즈 대기열** — 개인 부적합 |
| Sora 2 | — | **2026-09 API 종료 예정** | ❌ 제외 |

**결정**: 기본 후보는 Kling(가성비) 또는 Veo Fast(오디오 포함).
어느 쪽이든 `routing_table.json`의 `media.video.provider`만 바꾸면 교체된다.

## 파이프라인 (구현 완료)

```
주제 → 대본(Writer AI) → 장면 분할(JSON) → 장면별 영상 생성
→ 음성 → FFmpeg 편집(연결+한글 자막 번인) → 썸네일(제목 오버레이)
→ Quality Inspector → CEO 결재함 등록 (★업로드 안 함★)
```

산출물: `video/output/{job_id}/` — final.mp4(1080x1920 쇼츠),
thumbnail.jpg, subtitles.srt, scenes.json, script.txt

## Provider 상태 (정직한 표기)

| 모듈 | provider | 상태 |
|---|---|---|
| 영상 | placeholder | ✅ 테스트 통과 (FFmpeg 로컬, 무료) |
| 영상 | gemini_veo | ⚠ 어댑터 작성됨, **실제 키로 미검증** |
| 영상 | fal_kling | ⚠ 어댑터 작성됨, **실제 키로 미검증** |
| 음성 | silent | ✅ 테스트 통과 (무음 트랙) |
| 음성 | elevenlabs | ⚠ 어댑터 작성됨, **실제 키로 미검증** (voice_id 설정 필요) |

미검증 어댑터는 첫 실제 호출에서 API 응답 형식 차이로 수정이
필요할 수 있다. 오류 메시지를 가지고 다음 세션에서 조정하면 된다.

## Quality Inspector v1의 정직성 원칙

- 점수는 **규칙 기반**(길이, 해상도, 오디오 유무, 무음 감지, 제목 길이,
  나레이션 속도 등 확인 가능한 항목)이다.
- "예상 클릭률" 같은 예측 점수는 **넣지 않았다** — 근거 데이터 없이
  만드는 예측은 가짜이기 때문. 업로드 후 성과 데이터가 Memory 2.0에
  쌓이면 그때 데이터 기반으로 추가한다.
- 실제로 dry-run에서 무음(40점)과 경고를 정확히 감지함을 테스트로 확인.

## 사용법

```bash
# 키 없이 전체 구조 테스트 (placeholder 영상 생성됨)
python -m video.pipeline "주제" --dry-run

# 대본/장면은 실제 AI, 영상은 media.video.provider 설정을 따름
python -m video.pipeline "엔비디아 실적 핵심 3가지"
```

결과는 대시보드 CEO 결재함에서 영상 재생 + 썸네일 확인 후
승인/반려/재생성.

## 테스트 결과

- [x] dry-run 전체 파이프라인 → 실제 26초 mp4 생성 (tests/test_pipeline.py 4/4)
- [x] 해상도 1080x1920, 오디오 트랙 포함
- [x] 한글 자막 번인 렌더링 (Noto Sans CJK) — 프레임 캡처로 확인
- [x] 썸네일 제목 오버레이 확인
- [x] 결재함 pending 등록, 자동 업로드 없음
- [x] Quality Inspector 무음 감지 (음성 40점 + 경고)
- [ ] 실제 영상 AI 호출 (사용자 키 등록 후)
- [ ] 유튜브 업로드 (승인 후) — t13, 다음 작업

## 남은 작업 (3단계 마무리)

- t10: 영상 생성 AI 실제 연동 검증 (fal.ai 또는 Gemini 키 필요)
- t11: ElevenLabs 실제 연동 검증 (키 + voice_id 필요)
- t13: 승인 → 유튜브 업로드 (YouTube Data API, OAuth 필요 — 별도 세션 권장)

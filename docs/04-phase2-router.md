# 2단계 · AI Router (v0.2.0)

## 설계

AI Router는 "어떤 작업을 어떤 AI 직원에게 맡길지" 결정하는 인사팀이다.

```
작업 요청 (task, prompt)
        │
        ▼
routing_table.json 규칙 조회   ← 작업 유형별 provider/model/system 프롬프트
        │
        ▼
agents/ 어댑터 호출             ← anthropic / openai / gemini 동일 인터페이스
        │
        ▼
memory/ai_usage.json 기록      ← 시각, 토큰, 비용(설정 시) → 재무센터 데이터
        │
        ▼
결과 반환
```

## 핵심 설계 결정

1. **AI 교체는 설정 변경만으로**: `memory/routing_table.json`의 `provider`와
   `model`만 바꾸면 코드 수정 없이 즉시 교체된다. → "AI 자동 교체 제안"(AI 관리센터)의 기반.
2. **가격은 하드코딩하지 않는다**: API 가격은 수시로 바뀌므로 사용자가
   routing_table.json에 직접 입력한다. 미입력 시 토큰만 기록하고 "미산정" 표시.
3. **키는 .env에만**: 코드/JSON에 키를 절대 넣지 않는다. `.gitignore`에 포함.
4. **dry-run 모드**: 키 없이도 전체 파이프라인 구조를 테스트할 수 있다.
5. **AI PM 연동**: 첫 실제 대본 생성이 성공하면 작업 t7이 자동으로 완료 처리된다.

## 사용법

```bash
# 1) 키 등록 (한 번만)
cp .env.example .env    # 열어서 ANTHROPIC_API_KEY=sk-... 입력

# 2) 키 없이 구조 테스트
python -m router.cli "아무 주제" --dry-run

# 3) 실제 대본 생성
python -m router.cli "엔비디아 실적 발표 핵심 3가지"
```

## 테스트 결과

- [x] dry-run 라우팅 및 응답 (tests/test_router.py 6/6 통과)
- [x] 호출 기록 파일 저장
- [x] 가격 미설정 시 비용 None 처리
- [x] 잘못된 작업 유형 거부
- [x] 키 없을 때 한국어 안내 후 종료
- [x] 대시보드 /api/router/usage, Scoreboard 동적 상태 확인
- [ ] 실제 API 키로 호출 (← 사용자가 .env 등록 후 직접 확인, 성공 시 t7 자동 체크)

## 3단계 (영상 자동 제작) 착수 전 결정할 것

- [ ] 영상 생성 AI 선택 (Kling / Veo / Runway 중 — API 제공 여부와 가격 확인 필요)
- [ ] 음성 AI 선택 (ElevenLabs 등)
- [ ] 편집: FFmpeg 로컬 처리 확정 여부
- [ ] 대본 → 장면 분할 형식 (JSON 스키마) 정의

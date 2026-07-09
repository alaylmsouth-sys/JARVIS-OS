# 1단계 · JARVIS Dashboard (v0.1.0)

## 설계

- 스택: Python 3.10+ / FastAPI / 단일 HTML (외부 프론트 빌드 없음 — 단순 유지)
- 데이터: 전부 `memory/*.json` 파일. DB 없음 (필요해지면 SQLite로 전환)
- 화면 구성:
  1. AI Project Manager — 전체 진행률(10칸 세그먼트 바), 오늘의 우선순위 한 줄
  2. 다음 작업 — 단계별 체크리스트 (클릭으로 완료 토글 → 파일에 저장)
  3. AI Scoreboard — AI 직원 성적표 (Router 연결 전까지 "미연결" 표시)
  4. CEO 결재함 — 승인 대기 카드: 품질 점수, [승인 도장] [다시 만들기] [반려]

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | / | 대시보드 화면 |
| GET | /api/project | 진행률 + 오늘의 우선순위 |
| POST | /api/tasks/{id}/toggle | 작업 완료 토글 |
| GET | /api/scoreboard | AI 성적표 |
| GET | /api/approvals | 승인 큐 |
| POST | /api/approvals/{id}/{action} | approve / reject / retry |

## 테스트

- [x] 서버 기동 및 / 응답 200
- [x] /api/project 진행률 계산 정확 (완료 4 / 전체 17)
- [x] 작업 토글 후 project_state.json 저장 확인
- [x] 승인 → status "approved" 저장 확인

## 다음 세션에서 이어가는 방법 (중요)

AI 어시스턴트는 대화 세션 간 기억이 없다. 새 세션에서는:

1. 이 저장소(또는 zip)를 업로드하거나 GitHub 링크 제공
2. "docs/ 폴더를 읽고 이어서 2단계 AI Router를 진행해줘"라고 요청

모든 확정 사항은 docs/에, 모든 상태는 memory/에 있으므로
어떤 AI와 대화해도 이어서 작업할 수 있다.

## 2단계 (AI Router) 착수 전 결정할 것

- [ ] 첫 연결 AI 선택 (대본 생성용 1개부터 시작 권장)
- [ ] API 키 저장 방식 (.env 파일 + security/에서 관리)
- [ ] 라우팅 규칙: 작업 유형 → AI 매핑 테이블 초안
- [ ] 호출 비용 기록 → 재무센터의 "AI 사용료" 데이터로 연결

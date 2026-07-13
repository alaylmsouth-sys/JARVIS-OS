# JARVIS OS

> "AI 직원들이 일하고, 나는 CEO처럼 최종 승인만 하는 시스템."

## 실행 방법

1. Python 3.10+ 설치
2. 의존성 설치
   ```
   pip install -r requirements.txt
   ```
3. 실행
   - Windows: `run.bat` 더블클릭
   - Mac/Linux: `./run.sh`
4. 브라우저에서 http://127.0.0.1:8000 접속

## 현재 상태 (v0.10.0 — 10단계 영상 성과 분석)

- ✅ AI Project Manager: 진행률, 단계별 작업, 오늘의 우선순위
- ✅ AI Scoreboard: AI 직원 성적표 (아직 미연결 상태 표시)
- ✅ CEO 결재함: 승인/반려/재생성 (샘플 1건 포함)
- ✅ AI Router: 작업→AI 라우팅, 사용료 기록, dry-run (2단계)
- ✅ 영상 파이프라인: 대본→장면→영상→자막→썸네일→품질검사→결재함 (3단계, 실AI 연동 검증 대기)
- ✅ 영상 성과 분석: 조회수/좋아요/댓글 스냅샷 + 증감 추적, 스코어보드 연동 (10단계, 재인증 후 실API 검증 대기)

## 폴더 구조

```
JARVIS-OS/
├── dashboard/   # 웹 대시보드 (FastAPI + HTML)
├── brain/       # 핵심 로직 (project_manager 등)
├── router/      # (2단계) AI Router
├── agents/      # (3단계~) AI 직원들
├── finance/     # (4단계) 재무센터
├── video/       # (3단계) 영상 파이프라인
├── memory/      # 모든 상태 저장 (JSON) — 세션이 바뀌어도 유지
├── security/    # (추후) 백업/보안
├── plugins/
├── tests/
└── docs/        # 설계 문서
```

## 핵심 원칙

1. 모든 영상은 업로드 전에 반드시 CEO가 최종 검토하고 승인한다.
2. 중요한 작업(업로드, 투자 주문, 세금 신고 등)은 항상 사람의 최종 승인을 거친다.
3. JARVIS는 준비와 추천은 자동화하되, 중요한 결정은 사람이 내린다.
4. 모든 상태는 memory/ 폴더의 파일에 저장한다 (대화 세션에 의존하지 않음).

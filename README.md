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

## 검증

초기 실행 시 대시보드가 `memory/templates/`의 기본 파일을 `memory/`에 한 번만 생성하며, 기존 개인 데이터는 덮어쓰지 않습니다. 자동 검증은 다음 명령으로 실행합니다.

```bash
python -m pytest -q
```

영상 파이프라인의 구조 검증은 외부 AI·TTS·영상 생성 서비스를 호출하지 않도록 `--dry-run`에서 placeholder 영상과 무음 트랙을 강제합니다.

```bash
python -m video.pipeline "테스트 주제" --dry-run
```

## 현재 상태 (v1.0.0-rc — 5개 센터 큰 틀 완성)

- ✅ AI Project Manager: 진행률, 단계별 작업, 오늘의 우선순위
- ✅ AI Scoreboard: AI 직원 성적표 (아직 미연결 상태 표시)
- ✅ CEO 결재함: 승인/반려/재생성 (샘플 1건 포함)
- ✅ AI Router: 작업→AI 라우팅, 사용료 기록, dry-run (2단계)
- ✅ 영상 파이프라인: 대본→장면→영상→자막→썸네일→품질검사→결재함 (3단계, dry-run 자동 검증 완료·실AI 연동 검증 대기)
- ✅ 영상 성과 분석: 조회수/좋아요/댓글/시청시간 스냅샷 + 증감 추적 (실API 검증 대기)
- ✅ AI 관리센터: 역할별 배정/키/사용량/경고 (12단계)
- ✅ 시스템센터: 자가 점검 — 환경/인증/무결성/백업 (13단계)
- ⬜ 실환경 검증 5종: docs/14 표 참고 (키 설정 → 인증 → 업로드 1건)

## 폴더 구조

```
JARVIS-OS/
├── dashboard/   # 웹 대시보드 (FastAPI + HTML)
├── brain/       # 핵심 로직 (project_manager 등)
├── router/      # (2단계) AI Router
├── agents/      # (3단계~) AI 직원들
├── finance/     # (4단계) 재무센터
├── video/       # (3단계) 영상 파이프라인
├── memory/      # 내 데이터 (git 추적 안 함) — templates/에서 자동 생성
│   └── templates/ # 초기 템플릿 (저장소에 포함)
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
5. 코드는 공개, 내 데이터는 비공개: memory/*.json은 git에 올리지 않고 `./backup.sh`로 비공개 저장소(JARVIS-DATA)에 백업한다.

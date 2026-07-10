# 6단계 · 유튜브 업로드 (v0.6.0, t13)

## 원칙 (코드로 강제됨 — 테스트 4/4)

- status가 "approved"인 결재 항목만 업로드 가능 (미승인 → PermissionError/403)
- 업로드는 사용자의 명시적 실행(버튼/CLI)으로만. 자동 업로드 없음.
- 기본 공개 범위 private(비공개) → 유튜브 스튜디오에서 확인 후 직접 공개 전환.

## 사전 설정 (최초 1회, 약 10분)

1. https://console.cloud.google.com 접속 → 새 프로젝트 생성 (이름: JARVIS-OS)
2. "API 및 서비스 → 라이브러리" → **YouTube Data API v3** 검색 → 사용 설정
3. "API 및 서비스 → OAuth 동의 화면" → External 선택 → 앱 이름/이메일 입력
   → **테스트 사용자에 본인 Gmail 추가** (중요!)
4. "사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID"
   → 유형: **"TV 및 제한된 입력 장치"** ← 반드시 이 유형 (기기 코드 방식)
5. 발급된 클라이언트 ID/보안 비밀을 .env에 추가:
   ```
   YT_CLIENT_ID=...
   YT_CLIENT_SECRET=...
   ```

## 사용법

```bash
# 최초 1회 인증 (터미널에 뜨는 URL 접속 + 코드 입력)
python3 -m video.uploader auth

# 업로드: 대시보드 결재함에서 [승인] → [📤 유튜브 업로드] 버튼
# 또는 CLI:
python3 -m video.uploader upload <결재ID> --privacy private
```

첫 업로드 성공 시 t13이 자동 완료 처리된다 (AI PM 연동).

## 정직한 주의사항

- ⚠ **실제 OAuth/업로드는 개발 환경에서 미검증** — 구글 문서 기준 구현.
  첫 실행 오류 시 메시지를 다음 세션에 공유하면 조정한다.
- ⚠ OAuth 동의 화면이 "테스트" 상태(미인증 앱)면 토큰이 7일 후 만료될 수 있고,
  미인증 API 프로젝트의 업로드는 유튜브가 비공개로 잠글 수 있다.
  개인용으로는 문제없으며, 정식 운영 시 앱 인증 검토.
- 토큰 파일(memory/youtube_token.json)은 계정 접근 권한이므로 .gitignore 처리됨.
- 업로드 후 24시간 성과 분석(조회수/CTR)은 다음 단계(Memory 2.0) 과제.

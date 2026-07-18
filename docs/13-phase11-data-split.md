# 11단계 · 데이터 분리 (코드 공개 / 내 데이터 비공개)

## 배경

저장소를 퍼블릭으로 전환했다. 지금은 샘플 데이터뿐이라 안전하지만,
앞으로 실제 보유 종목·가계부 등을 넣으면 공개되는 구조였다.
→ **코드(JARVIS-OS, 공개)와 데이터(JARVIS-DATA, 비공개)를 완전히 분리**한다.

## 구조

```
JARVIS-OS   (공개)    코드 + memory/templates/ (초기 템플릿만)
JARVIS-DATA (비공개)  memory/*.json 백업 (내 실제 데이터)
내 실행 환경           memory/*.json (git 추적 안 함 — .gitignore)
```

- `.gitignore`에 `memory/*.json` 추가 — 개인 데이터는 커밋 불가
- `memory/templates/` — 각 파일의 초기 상태. 누가 clone해도 바로 실행 가능
- `brain/bootstrap.py` — 서버 시작 시 **없는 파일만** 템플릿에서 생성.
  **기존 파일은 절대 덮어쓰지 않는다** (테스트로 강제)
- `backup.sh` — 비공개 저장소로 백업(push) / `backup.sh restore` — 복원
- ⚠ `youtube_token.json`(계정 열쇠)은 **백업에서도 제외** — 열쇠는 어떤
  저장소에도 넣지 않는다. 유실 시 재인증 1회면 충분하다.

## 최초 1회 설정

1. github.com → New repository → 이름 `JARVIS-DATA` → **Private** →
   "Add a README" 체크 → 생성
2. (Codespaces) devcontainer에 데이터 저장소 쓰기 권한을 추가했으므로
   **Codespace 재빌드**: 명령 팔레트(F1) → "Codespaces: Rebuild Container"
3. 코드 저장소에서 기존 memory 추적 해제 (파일은 남고 git에서만 제거):
   ```
   git rm --cached memory/*.json
   git commit -m "11단계: memory 데이터 분리"
   git push
   ```
4. 첫 백업: `./backup.sh`

## 일상 사용

- 평소: 그냥 사용 — memory는 로컬에서만 변한다
- 백업하고 싶을 때(중요 데이터 입력 후, Codespace 오래 방치 전): `./backup.sh`
- 새 환경/복구: clone → `./backup.sh restore`

## 정직한 주의사항

- Codespace는 30일(기본) 미사용 시 삭제될 수 있다 → 실 데이터를 넣기
  시작하면 `./backup.sh`를 습관화할 것. 자동 백업은 만들지 않았다
  (원칙: 시키지 않은 push 없음). 필요해지면 다음 단계에서 논의.
- 퍼블릭 전환 이전 커밋 이력에는 예전 memory 파일들이 남아 있다.
  전부 샘플 데이터임을 확인했으므로 문제없다. 만약 과거에 민감 데이터를
  커밋한 적이 있었다면 이력 세척(git filter-repo)이 필요했을 것이다.

## 테스트 (tests/test_bootstrap.py — 4/4)

- 코드가 참조하는 모든 memory 파일에 템플릿 존재
- 없는 파일만 생성 / **기존 파일 절대 덮어쓰지 않음** / 멱등성
- 템플릿에 개인 데이터가 비어 있음 (커밋 실수 방지 가드)

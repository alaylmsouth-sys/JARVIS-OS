#!/usr/bin/env bash
# backup.sh — memory/ 데이터를 "비공개 데이터 저장소"에 백업/복원 (11단계 = t31)
#
# 구조: 코드는 공개(JARVIS-OS), 내 데이터는 비공개(JARVIS-DATA)로 완전 분리.
#
# 사용:
#   ./backup.sh            # memory/*.json → 비공개 저장소로 백업(push)
#   ./backup.sh restore    # 비공개 저장소 → memory/ 복원 (확인 후 덮어씀)
#
# 사전 준비 (최초 1회):
#   1. github.com 에서 비공개 저장소 JARVIS-DATA 생성 (README 추가 체크)
#   2. Codespaces라면 .devcontainer 권한 반영을 위해 Codespace 재빌드
#
# 원칙: youtube_token.json(계정 열쇠)은 백업하지 않는다.
#       열쇠는 어떤 저장소에도 넣지 않는다 — 유실 시 재인증 1회면 된다.

set -e
cd "$(dirname "$0")"

DATA_REPO="${JARVIS_DATA_REPO:-alaylmsouth-sys/JARVIS-DATA}"
DATA_DIR="${JARVIS_DATA_DIR:-$HOME/.jarvis-data}"

clone_if_needed() {
  if [ ! -d "$DATA_DIR/.git" ]; then
    echo "데이터 저장소 내려받는 중: $DATA_REPO"
    if command -v gh >/dev/null 2>&1; then
      gh repo clone "$DATA_REPO" "$DATA_DIR"
    else
      git clone "https://github.com/$DATA_REPO.git" "$DATA_DIR"
    fi
  fi
  git -C "$DATA_DIR" pull --quiet || true
}

case "${1:-backup}" in
  backup)
    clone_if_needed
    mkdir -p "$DATA_DIR/memory"
    copied=0
    for f in memory/*.json; do
      base="$(basename "$f")"
      [ "$base" = "youtube_token.json" ] && continue   # 열쇠는 백업 금지
      cp "$f" "$DATA_DIR/memory/$base"
      copied=$((copied+1))
    done
    cd "$DATA_DIR"
    git add -A
    if git diff --cached --quiet; then
      echo "✅ 변경 없음 — 이미 최신 백업입니다. (${copied}개 확인)"
    else
      git commit -q -m "backup: $(date '+%Y-%m-%d %H:%M')"
      git push -q
      echo "✅ 백업 완료: ${copied}개 파일 → $DATA_REPO"
    fi
    ;;
  restore)
    clone_if_needed
    if [ ! -d "$DATA_DIR/memory" ]; then
      echo "⚠ 데이터 저장소에 백업이 없습니다. 먼저 ./backup.sh 로 백업하세요."
      exit 1
    fi
    echo "⚠ 현재 memory/의 파일을 백업본으로 덮어씁니다."
    read -r -p "계속할까요? (yes 입력): " ans
    [ "$ans" = "yes" ] || { echo "취소됨"; exit 0; }
    cp "$DATA_DIR"/memory/*.json memory/
    echo "✅ 복원 완료. (유튜브는 재인증 필요 시: python3 -m video.uploader auth)"
    ;;
  *)
    echo "사용법: ./backup.sh [restore]"
    exit 1
    ;;
esac

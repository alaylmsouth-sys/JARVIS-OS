# 10단계 · 영상 성과 분석 (Analytics v1)

## 목표

워크플로우 v1의 미구현 구간을 채운다:

```
유튜브 업로드 → ★성과 분석★ → 기록 저장 → 다음 영상 개선
```

업로드된 영상의 **실측 지표(조회수/좋아요/댓글)** 를 유튜브 API로 가져와
`memory/video_performance.json`에 스냅샷으로 누적하고, 대시보드에서
증감 추이를 확인한다.

## 정직성 원칙 (이 단계의 규칙)

1. **사실만 기록한다.** API가 주지 않는 값(비공개 좋아요 수 등)은 None —
   지어내지 않는다.
2. **직원별 성과 귀속을 하지 않는다.** "조회수가 높은 건 Writer AI 덕분"
   같은 귀속은 검증 불가능한 판단이다. 조회수는 **영상 단위**로만 표시한다.
3. Scoreboard의 score는 "업로드가 승인·채택된 영상들의 품질 점수(규칙 기반)
   역할별 평균"으로 채우고, 그 사실을 status에 명시한다.
   (실측 성과가 아니라 채택작의 품질 예측치 평균임을 화면에 그대로 적는다.)
4. **자동 갱신 없음.** 사용자가 [↻ 갱신]을 누를 때만 API를 호출한다
   (쿼터 절약 + "JARVIS는 시키지 않은 네트워크 호출을 하지 않는다").

## 범위 (v1)

| 포함 | 제외 (v1.1 과제) |
|---|---|
| 조회수, 좋아요, 댓글 수 (Data API v3) | CTR, 노출수, 평균 시청시간 (**Analytics API** — 별도 스코프·API 활성화 필요) |
| 스냅샷 누적 → 이전 대비 증감 표시 | 성공 요인 자동 분석 (Memory 2.0 본편) |
| Scoreboard 채택작 품질 평균 | 댓글 내용 수집/감성 분석 |

## ⚠ 재인증 필요

기존 OAuth 스코프는 `youtube.upload` 뿐이라 **통계 조회가 403으로 거부**된다.
`security/youtube_auth.py`의 SCOPE에 `youtube.readonly`를 추가했으므로,
갱신 버튼이 권한 오류를 안내하면 한 번만 재인증한다:

```
python3 -m video.uploader auth
```

## 구조

```
video/analytics.py            # 스냅샷 수집·요약·스코어보드 갱신
memory/video_performance.json # {"videos":[{item_id, video_id, title, url,
                              #   snapshots:[{at, views, likes, comments}]}]}
```

- `sync_from_queue()` — 결재함에서 status=="uploaded" 항목을 성과 대장에 등록
- `snapshot(fetcher=None)` — 등록된 전 영상 통계 1회 조회 후 스냅샷 추가.
  fetcher 주입 가능 → 네트워크 없이 테스트
- `summary()` — 영상별 최신 스냅샷 + 직전 대비 증감(Δ) 계산
- `update_scoreboard()` — 채택작 품질 평균을 역할별 기록
  (대본→Writer, 음성→Voice, 영상→Video AI)

## 대시보드

- 새 섹션 **🎬 영상 성과**: 제목(유튜브 링크) / 업로드일 / 조회수(Δ) /
  좋아요 / 댓글 / 마지막 확인 시각 + [↻ 갱신]
- `GET /api/performance`, `POST /api/performance/refresh`
- 권한 오류 시 재인증 명령어를 화면에 그대로 안내

## 테스트 (네트워크 없이)

- [x] uploaded 상태 + video_id 있는 항목만 대장에 등록된다
- [x] 가짜 fetcher 주입 → 스냅샷 누적, 두 번째 스냅샷에서 Δ 계산 정확
- [x] API가 값을 숨기면(None) 그대로 None 저장 — 지어내지 않음
- [x] 스코어보드: 채택작 품질 평균이 역할별로 정확히 매핑
- [x] 업로드 영상이 없으면 빈 요약 + 안내 문구 (오류 아님)
- [ ] 실제 유튜브 API 호출 (사용자 환경 — 재인증 후 확인)

"""JARVIS OS Dashboard 서버.

실행:  python -m uvicorn dashboard.main:app --reload
접속:  http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain import project_manager as pm  # noqa: E402

MEMORY = ROOT / "memory"
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="JARVIS OS", version="0.3.0")

# 제작된 영상/썸네일을 결재함에서 미리볼 수 있게 마운트
from fastapi.staticfiles import StaticFiles  # noqa: E402
VIDEO_OUT = ROOT / "video" / "output"
VIDEO_OUT.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=VIDEO_OUT), name="media")


def _read_json(name: str) -> dict:
    with open(MEMORY / name, encoding="utf-8") as f:
        return json.load(f)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/project")
def api_project() -> JSONResponse:
    return JSONResponse({"progress": pm.progress(), "priority": pm.today_priority()})


@app.post("/api/tasks/{task_id}/toggle")
def api_toggle(task_id: str) -> JSONResponse:
    result = pm.toggle_task(task_id)
    status = 200 if result.get("ok") else 404
    return JSONResponse(result, status_code=status)


@app.get("/api/scoreboard")
def api_scoreboard() -> JSONResponse:
    from security.keys import has_key
    data = _read_json("scoreboard.json")
    table = _read_json("routing_table.json")
    writer_provider = table["routes"]["script"]["provider"]
    env_key = table["providers"][writer_provider]["env_key"]
    vprov = table.get("media", {}).get("voice", {}).get("provider", "silent")
    for agent in data["agents"]:
        if agent["name"] == "Voice AI":
            agent["status"] = (f"연결됨 ({vprov})" if vprov != "silent"
                               else "silent (TTS 미설정)")
        if agent["name"] == "Writer AI":
            agent["status"] = (
                f"연결됨 ({writer_provider})" if has_key(env_key)
                else f"키 필요 → .env에 {env_key} 추가"
            )
    return JSONResponse(data)


@app.get("/api/router/usage")
def api_router_usage() -> JSONResponse:
    from router.router import usage_summary
    return JSONResponse(usage_summary())


@app.get("/api/finance/summary")
def api_finance_summary() -> JSONResponse:
    from finance.finance import summary
    return JSONResponse(summary())


@app.post("/api/finance/entry")
def api_finance_entry(payload: dict) -> JSONResponse:
    from finance.finance import add_entry
    try:
        e = add_entry(payload.get("kind", ""), int(payload.get("amount", 0)),
                      payload.get("category", "기타"), payload.get("memo", ""))
        return JSONResponse({"ok": True, "entry": e})
    except (ValueError, TypeError) as err:
        return JSONResponse({"ok": False, "error": str(err)}, status_code=400)


@app.delete("/api/finance/entry/{entry_id}")
def api_finance_delete(entry_id: str) -> JSONResponse:
    from finance.finance import delete_entry
    ok = delete_entry(entry_id)
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


# ── 투자센터 ──────────────────────────────────────────

@app.get("/api/invest/summary")
def api_invest_summary() -> JSONResponse:
    from invest.portfolio import summary
    return JSONResponse(summary())


@app.post("/api/invest/holding")
def api_invest_add(payload: dict) -> JSONResponse:
    from invest.portfolio import add_holding
    try:
        h = add_holding(payload["ticker"], payload.get("name") or payload["ticker"],
                        float(payload["qty"]), float(payload["avg_price"]),
                        payload.get("currency", "KRW"))
        return JSONResponse({"ok": True, "holding": h})
    except (ValueError, KeyError, TypeError) as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.delete("/api/invest/holding/{hid}")
def api_invest_del(hid: str) -> JSONResponse:
    from invest.portfolio import remove_holding
    ok = remove_holding(hid)
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


@app.post("/api/invest/price/{hid}")
def api_invest_price(hid: str, payload: dict) -> JSONResponse:
    """수동 입력({"price": 123}) 또는 자동 조회({"fetch": true})."""
    from invest.portfolio import set_price, _load
    try:
        if payload.get("fetch"):
            from invest.prices import fetch_price
            h = next((x for x in _load()["holdings"] if x["id"] == hid), None)
            if not h:
                return JSONResponse({"ok": False, "error": "종목 없음"}, status_code=404)
            p = fetch_price(h["ticker"])
            updated = set_price(hid, p["price"], source="yahoo")
        else:
            updated = set_price(hid, float(payload["price"]), source="manual")
        return JSONResponse({"ok": True, "holding": updated})
    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/invest/event")
def api_invest_event(payload: dict) -> JSONResponse:
    from invest.portfolio import add_event
    try:
        e = add_event(payload["date"], payload["name"])
        return JSONResponse({"ok": True, "event": e})
    except (ValueError, KeyError) as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.delete("/api/invest/event/{eid}")
def api_invest_event_del(eid: str) -> JSONResponse:
    from invest.portfolio import remove_event
    ok = remove_event(eid)
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


@app.post("/api/invest/brief")
def api_invest_brief(payload: dict) -> JSONResponse:
    from invest.analyst import brief
    try:
        text = brief(payload.get("news", ""))
        return JSONResponse({"ok": True, "brief": text})
    except Exception as e:  # 키 미설정/모델 오류 등을 화면에 전달
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/charts")
def api_charts(refresh: bool = False) -> JSONResponse:
    from invest.charts import board
    from datetime import date as _d
    try:
        return JSONResponse(board(refresh=refresh))
    except Exception as e:
        return JSONResponse({"date": _d.today().isoformat(), "items": [],
                             "note": f"차트 보드 오류: {e}"})


@app.get("/api/detail/{ticker}")
def api_detail(ticker: str, interval: str = "1d") -> JSONResponse:
    from invest.detail import detail
    try:
        return JSONResponse(detail(ticker, interval))
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/news/{ticker}")
def api_news(ticker: str, summarize: bool = False) -> JSONResponse:
    from invest.detail import news, issue_summary
    try:
        items = news(ticker)
        summary = issue_summary(ticker, items) if (summarize and items) else None
        return JSONResponse({"ok": True, "items": items, "summary": summary})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/screen/{ticker}")
def api_screen(ticker: str) -> JSONResponse:
    """자동 분석: 지표 계산 + 체크리스트 자동 채점 (추천 아님)."""
    from invest.screener import screen
    try:
        return JSONResponse(screen(ticker))
    except RuntimeError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


# ── 매매 규율 (체크리스트 + 일지) ─────────────────────

@app.get("/api/discipline")
def api_discipline() -> JSONResponse:
    from invest.discipline import load_rules, journal, stats
    return JSONResponse({"rules": load_rules(), "journal": journal(),
                         "stats": stats()})


@app.post("/api/discipline/trade")
def api_discipline_trade(payload: dict) -> JSONResponse:
    from invest.discipline import open_trade
    try:
        t = open_trade(payload["ticker"], payload.get("name") or payload["ticker"],
                       float(payload["qty"]), float(payload["price"]),
                       float(payload["stop_loss_pct"]), float(payload["target_pct"]),
                       payload.get("reason", ""), payload.get("checked", []))
        return JSONResponse({"ok": True, "trade": t})
    except (ValueError, KeyError, TypeError) as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/discipline/close/{tid}")
def api_discipline_close(tid: str, payload: dict) -> JSONResponse:
    from invest.discipline import close_trade
    try:
        return JSONResponse({"ok": True, "trade": close_trade(tid, float(payload["price"]))})
    except (ValueError, KeyError, TypeError) as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/discipline/review/{tid}")
def api_discipline_review(tid: str, payload: dict) -> JSONResponse:
    from invest.discipline import review_trade
    try:
        return JSONResponse({"ok": True, "trade": review_trade(
            tid, bool(payload.get("followed_plan")), payload.get("note", ""))})
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/approvals")
def api_approvals() -> JSONResponse:
    return JSONResponse(_read_json("approval_queue.json"))


@app.post("/api/upload/{item_id}")
def api_upload(item_id: str, payload: dict) -> JSONResponse:
    """승인된 항목만 업로드. 사용자의 명시적 버튼 클릭으로만 호출됨."""
    from video.uploader import upload
    try:
        r = upload(item_id, payload.get("privacy", "private"))
        return JSONResponse({"ok": True, **r})
    except PermissionError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=403)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/approvals/{item_id}/{action}")
def api_approval_action(item_id: str, action: str) -> JSONResponse:
    """승인 처리. action: approve | reject | retry
    ⚠ 핵심 원칙: 여기서 '승인' 표시만 한다. 실제 업로드는
    3단계(영상 파이프라인)에서도 이 승인 없이는 절대 실행되지 않는다."""
    if action not in {"approve", "reject", "retry"}:
        return JSONResponse({"ok": False, "error": "invalid action"}, status_code=400)
    data = _read_json("approval_queue.json")
    for item in data["items"]:
        if item["id"] == item_id:
            item["status"] = {"approve": "approved", "reject": "rejected", "retry": "retry"}[action]
            with open(MEMORY / "approval_queue.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return JSONResponse({"ok": True, "item": item})
    return JSONResponse({"ok": False, "error": "not found"}, status_code=404)

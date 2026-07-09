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
    for agent in data["agents"]:
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


@app.get("/api/approvals")
def api_approvals() -> JSONResponse:
    return JSONResponse(_read_json("approval_queue.json"))


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

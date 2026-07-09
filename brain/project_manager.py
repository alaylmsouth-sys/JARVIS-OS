"""AI Project Manager — JARVIS OS의 두뇌 중 프로젝트 관리 담당.

memory/project_state.json 을 읽어서:
  - 전체 진행률 계산
  - 현재 진행 중인 단계 파악
  - "오늘의 최우선 작업" 결정
을 담당한다. 데이터는 항상 파일에 저장되므로 세션이 바뀌어도 유지된다.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "memory" / "project_state.json"


def load_state() -> dict:
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def progress(state: dict | None = None) -> dict:
    """전체/단계별 진행률을 계산한다."""
    state = state or load_state()
    total = done = 0
    phases = []
    for phase in state["phases"]:
        p_total = len(phase["tasks"])
        p_done = sum(1 for t in phase["tasks"] if t["done"])
        total += p_total
        done += p_done
        phases.append(
            {
                "id": phase["id"],
                "name": phase["name"],
                "done": p_done,
                "total": p_total,
                "percent": round(p_done / p_total * 100) if p_total else 0,
                "tasks": phase["tasks"],
            }
        )
    return {
        "project": state["project"],
        "version": state["version"],
        "percent": round(done / total * 100) if total else 0,
        "done": done,
        "total": total,
        "phases": phases,
    }


def today_priority(state: dict | None = None) -> dict:
    """오늘의 최우선 작업 = 가장 앞 단계에서 아직 끝나지 않은 첫 작업."""
    state = state or load_state()
    for phase in state["phases"]:
        for task in phase["tasks"]:
            if not task["done"]:
                remaining = sum(1 for t in phase["tasks"] if not t["done"])
                return {
                    "phase": phase["name"],
                    "task": task["title"],
                    "task_id": task["id"],
                    "message": (
                        f"오늘은 「{task['title']}」을(를) 완료하는 것이 "
                        f"가장 중요합니다. ({phase['name']}, 남은 작업 {remaining}개)"
                    ),
                }
    return {
        "phase": None,
        "task": None,
        "task_id": None,
        "message": "모든 작업이 완료되었습니다. 다음 스프린트를 계획하세요.",
    }


def toggle_task(task_id: str) -> dict:
    """작업 완료/미완료 전환 후 저장."""
    state = load_state()
    for phase in state["phases"]:
        for task in phase["tasks"]:
            if task["id"] == task_id:
                task["done"] = not task["done"]
                save_state(state)
                return {"ok": True, "task": task}
    return {"ok": False, "error": f"task {task_id} not found"}


if __name__ == "__main__":
    p = progress()
    bar = "█" * (p["percent"] // 10) + "░" * (10 - p["percent"] // 10)
    print(f"{p['project']} v{p['version']}")
    print(f"진행률  {bar} {p['percent']}%  ({p['done']}/{p['total']})")
    print(today_priority()["message"])

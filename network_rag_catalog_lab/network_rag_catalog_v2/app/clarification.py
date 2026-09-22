"""Persisted clarification state shared by the terminal and a future web UI."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from uuid import uuid4

from .config import SESSIONS_DIR
from .pipeline import plan_to_dict, resume_task, run
from .planner.models import ExecutionPlan, OperationIntent, PlannedTask


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ClarificationSession:
    session_id: str
    created_at: str
    updated_at: str
    status: str
    plan: ExecutionPlan
    history: list[dict] = field(default_factory=list)

    @property
    def pending_tasks(self) -> list[PlannedTask]:
        return [task for task in self.plan.tasks if task.status == "needs_clarification"]


def _session_path(session_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9-]{36}", session_id):
        raise ValueError("Invalid clarification session ID.")
    return SESSIONS_DIR / f"{session_id}.json"


def _plan_from_dict(data: dict) -> ExecutionPlan:
    intents = [OperationIntent(**intent) for intent in data.get("intents", [])]
    tasks = [PlannedTask(**task) for task in data.get("tasks", [])]
    return ExecutionPlan(original_prompt=data["original_prompt"], intents=intents, tasks=tasks)


def session_to_dict(session: ClarificationSession) -> dict:
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "status": session.status,
        "plan": plan_to_dict(session.plan),
        "history": session.history,
    }


def _refresh_status(session: ClarificationSession) -> None:
    session.status = "needs_clarification" if session.pending_tasks else "ready"
    session.updated_at = _timestamp()


def save_session(session: ClarificationSession) -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = _session_path(session.session_id)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(session_to_dict(session), indent=2), encoding="utf-8")
    temporary.replace(target)


def load_session(session_id: str) -> ClarificationSession:
    path = _session_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"Clarification session not found: {session_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return ClarificationSession(
        session_id=data["session_id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        status=data["status"],
        plan=_plan_from_dict(data["plan"]),
        history=data.get("history", []),
    )


def create_session(prompt: str, *, verbose: bool = False) -> ClarificationSession:
    plan = run(prompt, verbose=verbose)
    now = _timestamp()
    session = ClarificationSession(
        session_id=str(uuid4()),
        created_at=now,
        updated_at=now,
        status="ready",
        plan=plan,
        history=[{"at": now, "type": "request", "text": prompt}],
    )
    _refresh_status(session)
    save_session(session)
    return session


def apply_clarification(
    session: ClarificationSession,
    task_id: str,
    reply: str,
    *,
    verbose: bool = False,
) -> ClarificationSession:
    for index, task in enumerate(session.plan.tasks):
        if task.intent_id != task_id:
            continue
        if task.status != "needs_clarification":
            raise ValueError(f"Task {task_id} is already ready.")
        session.plan.tasks[index] = resume_task(task, reply, verbose=verbose)
        session.history.append({"at": _timestamp(), "type": "clarification", "task_id": task_id, "text": reply})
        _refresh_status(session)
        save_session(session)
        return session
    raise KeyError(f"No task named {task_id} exists in session {session.session_id}.")

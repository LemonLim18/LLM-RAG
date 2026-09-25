"""Persisted clarification state shared by the terminal and a future web UI."""

from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from uuid import uuid4

from .config import SESSIONS_DIR
from .pipeline import confirm_order, correct_task, plan_to_dict, refresh_plan, resume_task, run
from .planner.models import ClarificationAnswer, ExecutionPlan, OperationIntent, PlannedTask


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

    @property
    def pending_questions(self) -> list[dict]:
        questions = [question for task in self.pending_tasks for question in task.questions]
        return sorted(questions, key=lambda question: 0 if question["field_path"] == "operation_id" else 1 if question["field_path"] == "target_refs" else 2)

    @property
    def next_question(self) -> dict | None:
        return next(iter(self.pending_questions), None)


def _session_path(session_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9-]{36}", session_id):
        raise ValueError("Invalid clarification session ID.")
    return SESSIONS_DIR / f"{session_id}.json"


def _plan_from_dict(data: dict) -> ExecutionPlan:
    version = data.get("schema_version", 1)
    if version not in {1, 2}:
        raise ValueError(f"Unsupported saved plan version: {version}")
    intents = [OperationIntent(**intent) for intent in data.get("intents", [])]
    tasks = [PlannedTask(**task) for task in data.get("tasks", [])]
    for task in tasks:
        if not task.target_queries:
            from .devices.inventory import load_inventory
            from .devices.target_query import parse_description
            task.target_queries = [parse_description(ref, load_inventory()) for ref in task.target_refs]
        task.logical_intent_id = task.logical_intent_id or task.intent_id
        # Old rendered outputs must cross the new request-wide gate on resume.
        task.configs = []
        task.status = "collecting"
    extra = {key: value for key, value in data.items() if key in {item.name for item in fields(ExecutionPlan)} - {"original_prompt", "intents", "tasks", "schema_version"}}
    return ExecutionPlan(original_prompt=data["original_prompt"], intents=intents, tasks=tasks, **extra)


def session_to_dict(session: ClarificationSession) -> dict:
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "status": session.status,
        "plan": plan_to_dict(session.plan),
        "history": session.history,
        "schema_version": 2,
        "pending_questions": session.pending_questions,
    }


def _refresh_status(session: ClarificationSession) -> None:
    session.status = session.plan.status
    session.updated_at = _timestamp()


def save_session(session: ClarificationSession) -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = _session_path(session.session_id)
    temporary = target.with_suffix(f".{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(session_to_dict(session), indent=2), encoding="utf-8")
    temporary.replace(target)


def load_session(session_id: str) -> ClarificationSession:
    path = _session_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"Clarification session not found: {session_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    session = ClarificationSession(
        session_id=data["session_id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        status=data["status"],
        plan=_plan_from_dict(data["plan"]),
        history=data.get("history", []),
    )
    refresh_plan(session.plan)
    _refresh_status(session)
    return session


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
    reply: str | ClarificationAnswer,
    *,
    verbose: bool = False,
) -> ClarificationSession:
    for index, task in enumerate(session.plan.tasks):
        if task.intent_id != task_id:
            continue
        if task.status != "needs_clarification":
            raise ValueError(f"Task {task_id} is already ready.")
        session.plan.tasks[index] = resume_task(task, reply, verbose=verbose)
        session.history.append({"at": _timestamp(), "type": "clarification", "task_id": task_id,
                                "text": reply if isinstance(reply, str) else reply.raw_input,
                                "accepted": not bool(session.plan.tasks[index].feedback)})
        refresh_plan(session.plan)
        _refresh_status(session)
        save_session(session)
        return session
    raise KeyError(f"No task named {task_id} exists in session {session.session_id}.")


def apply_answer(session: ClarificationSession, answer: ClarificationAnswer) -> ClarificationSession:
    question = session.next_question
    if not question or question["question_id"] != answer.question_id:
        raise ValueError("Answer the current question; this answer is stale or belongs to another task.")
    return apply_clarification(session, question["task_id"], answer)


def apply_correction(session: ClarificationSession, task_id: str, path: str, reply: str) -> ClarificationSession:
    for index, task in enumerate(session.plan.tasks):
        if task.intent_id == task_id:
            session.plan.tasks[index] = correct_task(task, path, reply)
            session.history.append({"at": _timestamp(), "type": "correction", "task_id": task_id, "field": path,
                                    "accepted": not bool(session.plan.tasks[index].feedback)})
            refresh_plan(session.plan)
            _refresh_status(session)
            save_session(session)
            return session
    raise KeyError(f"Unknown task {task_id}")


def confirm_session_order(session: ClarificationSession) -> ClarificationSession:
    confirm_order(session.plan)
    session.history.append({"at": _timestamp(), "type": "confirm_order"})
    _refresh_status(session)
    save_session(session)
    return session

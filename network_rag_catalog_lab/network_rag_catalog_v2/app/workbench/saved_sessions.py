"""Passive byte snapshot and lossless validation shared by GET and answer mutation.

Do not import clarification/pipeline here: those import model clients. Only answer
mutation constructs a ClarificationSession after these checks have succeeded.
"""
from hashlib import sha256
import json
from uuid import UUID

from pydantic import ValidationError

from .planning_models import SavedSessionResponse, SessionPayload
from .planning_service import PlanningError


def read_saved_bytes(session_id: str):
    from app.config import SESSIONS_DIR

    try:
        canonical = str(UUID(session_id))
    except ValueError as error:
        raise PlanningError(422, "INVALID_SESSION_ID", "A valid session UUID is required.") from error
    try:
        root = SESSIONS_DIR.resolve()
        path = root / f"{canonical}.json"
        if path.resolve().parent != root:
            raise PlanningError(409, "INVALID_SAVED_SESSION", "The saved session is outside configured storage.")
        return path, path.read_bytes()
    except FileNotFoundError as error:
        raise PlanningError(404, "SESSION_NOT_FOUND", "The saved session does not exist.") from error
    except OSError as error:
        raise PlanningError(503, "SESSION_STORAGE_UNAVAILABLE", "Saved session storage is unavailable.") from error


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Nonfinite JSON")


def validate_saved_payload(raw: bytes, session_id: str) -> SessionPayload:
    try:
        data = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        if not isinstance(data, dict) or not isinstance(data.get("plan"), dict):
            raise ValueError("Invalid structure")
        if data.get("schema_version") != 2 or data["plan"].get("schema_version") != 2:
            raise PlanningError(409, "UNSUPPORTED_SESSION_VERSION", "Only version-2 saved sessions are supported. No migration was performed.")
        payload = SessionPayload.model_validate(data)
        # Detect defaults, coercions, unknown dataclass fields, and any loss of data.
        if payload.session_id != session_id or json.dumps(payload.model_dump(mode="json"), sort_keys=True, allow_nan=False) != json.dumps(data, sort_keys=True, allow_nan=False):
            raise ValueError("Lossy payload")
        if payload.status != payload.plan.status:
            raise ValueError("Inconsistent session status")
        tasks = payload.plan.tasks
        task_ids = [task.intent_id for task in tasks]
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("Duplicate task identity")
        # Same ordering as ClarificationSession.pending_questions, without importing
        # the runtime. Answer restoration also checks session_to_dict equality.
        pending = [question for task in tasks if task.status == "needs_clarification" for question in task.questions]
        pending.sort(key=lambda question: 0 if question["field_path"] == "operation_id" else 1 if question["field_path"] == "target_refs" else 2)
        if pending != payload.pending_questions:
            raise ValueError("Inconsistent pending questions")
        question_ids = []
        for task in tasks:
            for question in task.questions:
                if question["task_id"] != task.intent_id or not isinstance(question["question_id"], str):
                    raise ValueError("Inconsistent question identity")
                question_ids.append(question["question_id"])
        if len(set(question_ids)) != len(question_ids):
            raise ValueError("Duplicate question identity")
        return payload
    except (ValueError, UnicodeError, ValidationError, KeyError, TypeError, RecursionError) as error:
        raise PlanningError(409, "INVALID_SAVED_SESSION", "Saved session is invalid or cannot be restored losslessly. No refresh or write was performed.") from error


def get_saved_session(session_id: str) -> SavedSessionResponse:
    _, raw = read_saved_bytes(session_id)
    payload = validate_saved_payload(raw, session_id)
    return SavedSessionResponse(session_revision=sha256(raw).hexdigest(), session=payload)

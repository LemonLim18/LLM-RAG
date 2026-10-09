"""Restore without refresh; called only while the shared planning gate is held."""
from hashlib import sha256
from .planning_models import AnswerRequest, AnswerResponse
from .planning_service import PlanningError, session_response
from .saved_sessions import read_saved_bytes, validate_saved_payload


def apply_saved_answer(session_id: str, request: AnswerRequest) -> AnswerResponse:
    from app.config import runtime_mode
    from app.clarification import ClarificationSession, apply_answer, session_to_dict
    from app.context import context_revision, source_revision
    from app.knowledge.runtime import snapshot_scope
    from app.planner.models import ClarificationAnswer
    from app.questions import selected_options

    path, raw = read_saved_bytes(session_id)
    if sha256(raw).hexdigest() != request.expected_session_revision:
        raise PlanningError(409, "STALE_SESSION", "Saved session revision changed. This answer was not applied; review the current session outside this workflow.")
    payload = validate_saved_payload(raw, session_id)
    session = ClarificationSession(payload.session_id, payload.created_at, payload.updated_at,
                                   payload.status, payload.plan, payload.history)
    if session_to_dict(session) != payload.model_dump(mode="json"):
        raise PlanningError(409, "INVALID_SAVED_SESSION", "Saved session cannot be restored losslessly. No refresh or write was performed.")
    question = session.next_question
    if session.status != "needs_clarification" or not question:
        raise PlanningError(409, "SESSION_NOT_ANSWERABLE", "This session has no eligible pending clarification.")
    answer = ClarificationAnswer(**request.answer.model_dump())
    if answer.question_id != question["question_id"]:
        raise PlanningError(409, "QUESTION_NOT_CURRENT", "Answer only the current pending question. This answer was not applied.")
    if (answer.revision, answer.source_revision) != (question["revision"], question["source_revision"]):
        raise PlanningError(409, "STALE_QUESTION", "Question revision changed. This answer was not applied.")
    if answer.kind == "custom" and not question.get("allow_custom", False):
        raise PlanningError(422, "CUSTOM_NOT_ALLOWED", "This question requires a listed option.")
    try:
        selected_options(question, answer)
    except ValueError as error:
        raise PlanningError(422, "INVALID_OPTION", str(error)) from error
    with snapshot_scope() as snapshot:
        current_authority = "published" if snapshot else runtime_mode()
        if (session.plan.runtime_authority != current_authority
                or session.plan.knowledge_snapshot_id != (snapshot.release_id if snapshot else "")
                or source_revision() != question["source_revision"]
                or context_revision() != session.plan.context_revision):
            raise PlanningError(409, "STALE_SOURCE", "Knowledge or inventory context changed. No answer was applied; explicit review is required.")
        if path.read_bytes() != raw:
            raise PlanningError(409, "STALE_SESSION", "Saved session changed before application. No answer was applied.")
        before_history = len(session.history)
        updated = apply_answer(session, answer)
        response = session_response(updated, request.client_request_id)
        accepted = (len(updated.history) == before_history + 1
                    and updated.history[-1].get("type") == "clarification"
                    and updated.history[-1].get("accepted") is True)
        if not accepted:
            task = next((task for task in updated.plan.tasks if task.intent_id == question["task_id"]), None)
            raise PlanningError(422, "V9_ANSWER_REJECTED", task.feedback if task and task.feedback else "V9 rejected this answer.", response)
        return AnswerResponse(**response.model_dump(), answered_question_id=answer.question_id)

"""Bounded, single-process adapter; V9 owns planning and session persistence."""

from hashlib import sha256
import json
from threading import Lock

from .planning_models import AnswerRequest, AnswerResponse, CreationOutcome, PlanningRequest, PlanningResponse, SessionPayload


class PlanningError(Exception):
    def __init__(self, status: int, code: str, message: str, current_session=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.current_session = current_session


def session_response(session, request_id) -> PlanningResponse:
    from app.clarification import session_to_dict
    from app.config import SESSIONS_DIR
    raw = (SESSIONS_DIR / f"{session.session_id}.json").read_bytes()
    serialized = session_to_dict(session)
    if json.loads(raw) != serialized:
        raise PlanningError(409, "SESSION_CHANGED", "Saved session changed during the operation. Do not blindly retry.")
    return PlanningResponse(client_request_id=request_id, session_revision=sha256(raw).hexdigest(),
                            session=SessionPayload.model_validate(serialized))


class PlanningService:
    def __init__(self):
        self._lock = Lock()
        self._busy = False
        # Never evict IDs and inadvertently execute a retried request again.
        self._requests: dict[str, tuple[str, PlanningResponse | PlanningError | None]] = {}

    def register_inventory_device(self, request):
        from .inventory_registration import register_device
        with self._lock:
            if self._busy:
                raise PlanningError(503, 'PLANNER_BUSY', 'The local mutation worker is busy. No inventory registration was started.')
            self._busy = True
        try:
            return register_device(request)
        finally:
            with self._lock:
                self._busy = False

    def _execute(self, request_id, fingerprint, operation, replay=None):
        key = str(request_id)
        with self._lock:
            if key in self._requests:
                prompt, outcome = self._requests[key]
                if prompt != fingerprint:
                    raise PlanningError(409, "REQUEST_ID_CONFLICT", "This request ID already belongs to another operation or payload.")
            if replay is not None:
                restored = replay()
                if restored is not None:
                    return restored
            if key in self._requests:
                _, outcome = self._requests[key]
                if isinstance(outcome, PlanningError):
                    raise outcome
                if outcome is not None:
                    return outcome
                raise PlanningError(409, "REQUEST_IN_PROGRESS", "V9 is still processing this request. Retry the same request ID later.")
            if self._busy:
                raise PlanningError(503, "PLANNER_BUSY", "The local V9 worker is busy. Retry the same request later.")
            if len(self._requests) >= 256:
                raise PlanningError(503, "REQUEST_CAPACITY", "Request retention is full. Review saved sessions before restarting the backend.")
            self._requests[key] = (fingerprint, None)
            self._busy = True

        try:
            outcome = operation()
        except PlanningError as error:
            outcome = error
        except Exception as error:
            from httpx import TransportError
            from ollama import ResponseError

            if isinstance(error, (ConnectionError, TimeoutError, TransportError, ResponseError)):
                outcome = PlanningError(503, "LOCAL_SERVICE_UNAVAILABLE", "A local model service failed or timed out. No demo response was substituted.")
            else:
                outcome = PlanningError(500, "V9_PLANNING_FAILED", "V9 could not return a planning session. Check backend diagnostics and saved sessions before starting a new request.")
            # Log type only: prompts, local paths and upstream exception bodies may be sensitive.
            import logging
            logging.getLogger(__name__).warning("Planning request %s failed (%s)", key, type(error).__name__)
        with self._lock:
            # Publish the outcome before permitting the next mutation.
            self._requests[key] = (fingerprint, outcome)
            self._busy = False
        if isinstance(outcome, PlanningError):
            raise outcome
        return outcome

    def create(self, request: PlanningRequest) -> PlanningResponse:
        from .creation_receipts import CreationReceipt, confirmed_session, read_receipt, request_fingerprint, write_receipt
        key = str(request.client_request_id)
        identity = request_fingerprint(request.prompt, request.mode)

        def replay():
            receipt = read_receipt(request.client_request_id)
            if receipt is None:
                if key in self._requests and isinstance(self._requests[key][1], PlanningResponse):
                    raise PlanningError(409, "RECEIPT_INCONSISTENT", "A confirmed creation receipt is missing. No replay is permitted.")
                return None
            if receipt.fingerprint != identity or receipt.mode != request.mode:
                raise PlanningError(409, "REQUEST_ID_CONFLICT", "This creation request ID belongs to different content.")
            if receipt.status == "completed":
                saved = confirmed_session(receipt)
                return PlanningResponse(client_request_id=request.client_request_id,
                                        session_revision=saved.session_revision, session=saved.session)
            if receipt.status == "terminal_error":
                raise PlanningError(503, "CREATOR_UNAVAILABLE", "The recorded request failed before invoking V9. It will not be replayed.")
            if key in self._requests:
                outcome = self._requests[key][1]
                if isinstance(outcome, PlanningError):
                    raise outcome
                if outcome is None:
                    raise PlanningError(409, "REQUEST_IN_PROGRESS", "Creation is still running. Check its outcome; do not submit another request.")
            raise PlanningError(409, "CREATION_INDETERMINATE", "Creation may have saved a session before interruption. This request cannot be replayed.")

        def operation():
            receipt = CreationReceipt(client_request_id=request.client_request_id, fingerprint=identity, status="accepted")
            write_receipt(receipt, initial=True)
            try:
                from app.clarification import create_session
            except Exception as error:
                write_receipt(receipt.model_copy(update={"status": "terminal_error", "error_code": "CREATOR_UNAVAILABLE"}))
                raise PlanningError(503, "CREATOR_UNAVAILABLE", "V9 could not be loaded. Creation was not invoked.") from error
            # Any failure from this point may have saved a session. Retain accepted,
            # never infer that an exception means no side effects occurred.
            result = session_response(create_session(request.prompt, verbose=False), request.client_request_id)
            completed = CreationReceipt.model_validate({**receipt.model_dump(), "status": "completed",
                "session_id": result.session.session_id, "session_created_at": result.session.created_at})
            confirmed_session(completed)
            write_receipt(completed)
            return result
        return self._execute(request.client_request_id, "create:" + request.model_dump_json(), operation, replay)

    def lookup_creation(self, request_id) -> CreationOutcome:
        from .creation_receipts import confirmed_session, read_receipt
        try:
            # Read and inspect process-local activity under the same small gate.
            # Never acquire the long-running V9 mutation operation itself.
            with self._lock:
                receipt = read_receipt(request_id)
                active = (str(request_id) in self._requests and self._requests[str(request_id)][1] is None)
            if receipt is None:
                return CreationOutcome(client_request_id=request_id, status="unknown",
                    message="No durable record is known. This does not prove that an earlier request had no side effects.")
            if receipt.status == "completed":
                saved = confirmed_session(receipt)
                return CreationOutcome(client_request_id=request_id, status="completed", session_id=receipt.session_id,
                    session_revision=saved.session_revision, message="Creation is recorded. Retrieve the saved session for historical review; current validity is not checked.")
            if receipt.status == "terminal_error":
                return CreationOutcome(client_request_id=request_id, status="terminal_error", error_code=receipt.error_code,
                    message="Creation failed before V9 was invoked. This request will not be replayed.")
            return CreationOutcome(client_request_id=request_id, status="in_progress" if active else "indeterminate",
                message="Creation is running in this process. Check again later." if active else
                "Creation was accepted but its outcome cannot be proved. A saved session may exist. Do not replay this request.")
        except PlanningError as error:
            if error.status != 409:
                raise
            return CreationOutcome(client_request_id=request_id, status="corrupt", error_code=error.code,
                message=str(error))

    def answer(self, session_id: str, request: AnswerRequest) -> AnswerResponse:
        from .creation_receipts import read_receipt
        if read_receipt(request.client_request_id) is not None:
            raise PlanningError(409, "REQUEST_ID_CONFLICT", "This request ID belongs to a creation operation.")
        from .answer_service import apply_saved_answer
        return self._execute(request.client_request_id, "answer:" + session_id + ":" + request.model_dump_json(),
                             lambda: apply_saved_answer(session_id, request))

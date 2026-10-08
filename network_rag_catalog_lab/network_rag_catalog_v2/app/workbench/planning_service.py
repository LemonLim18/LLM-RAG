"""Bounded, single-process adapter; V9 owns planning and session persistence."""

from hashlib import sha256
from threading import Lock

from .planning_models import PlanningRequest, PlanningResponse, SessionPayload


class PlanningError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


class PlanningService:
    def __init__(self):
        self._lock = Lock()
        self._busy = False
        # Never evict IDs and inadvertently execute a retried request again.
        self._requests: dict[str, tuple[str, PlanningResponse | PlanningError | None]] = {}

    def create(self, request: PlanningRequest) -> PlanningResponse:
        key = str(request.client_request_id)
        with self._lock:
            if key in self._requests:
                prompt, outcome = self._requests[key]
                if prompt != request.prompt:
                    raise PlanningError(409, "REQUEST_ID_CONFLICT", "This request ID already belongs to another prompt.")
                if isinstance(outcome, PlanningError):
                    raise outcome
                if outcome is not None:
                    return outcome
                raise PlanningError(409, "REQUEST_IN_PROGRESS", "V9 is still processing this request. Retry the same request ID later.")
            if self._busy:
                raise PlanningError(503, "PLANNER_BUSY", "The local V9 worker is busy. Retry the same request later.")
            if len(self._requests) >= 256:
                raise PlanningError(503, "REQUEST_CAPACITY", "Request retention is full. Review saved sessions before restarting the backend.")
            self._requests[key] = (request.prompt, None)
            self._busy = True

        try:
            # Lazy imports keep passive health/inventory requests model-independent.
            from app.clarification import create_session, session_to_dict
            from app.config import SESSIONS_DIR

            session = create_session(request.prompt, verbose=False)
            payload = SessionPayload.model_validate(session_to_dict(session))
            revision = sha256((SESSIONS_DIR / f"{session.session_id}.json").read_bytes()).hexdigest()
            outcome = PlanningResponse(client_request_id=request.client_request_id,
                                       session_revision=revision, session=payload)
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
        finally:
            with self._lock:
                # A worker continues after an HTTP disconnect; retain its eventual outcome.
                self._busy = False
        with self._lock:
            self._requests[key] = (request.prompt, outcome)
        if isinstance(outcome, PlanningError):
            raise outcome
        return outcome

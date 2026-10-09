"""Bounded creation receipts, not a planner or a second session store.

Single workbench process only. An accepted receipt is never permission to replay.
"""
from hashlib import sha256
from itertools import islice
import json
import os
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, ValidationError, model_validator

from .models import ResponseModel
from .planning_service import PlanningError
from .saved_sessions import _unique_object, _reject_constant, get_saved_session

MAX_RECEIPTS = 1024
MAX_RECEIPT_BYTES = 4096


class CreationReceipt(ResponseModel):
    version: Literal[1] = 1
    client_request_id: UUID
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    mode: Literal["local_v9"] = "local_v9"
    status: Literal["accepted", "completed", "terminal_error"]
    session_id: UUID | None = None
    session_created_at: str | None = None
    error_code: Literal["CREATOR_UNAVAILABLE"] | None = None

    @model_validator(mode="after")
    def check_outcome(self):
        completed = self.status == "completed"
        if completed != (self.session_id is not None and self.session_created_at is not None):
            raise ValueError("Incomplete session association")
        if not completed and (self.session_id is not None or self.session_created_at is not None):
            raise ValueError("Unexpected session association")
        if (self.status == "terminal_error") != (self.error_code is not None):
            raise ValueError("Inconsistent terminal error")
        return self


def request_fingerprint(prompt: str, mode: str) -> str:
    return sha256(json.dumps({"prompt": prompt, "mode": mode}, sort_keys=True,
                             ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def receipt_path(request_id):
    from app.config import SESSIONS_DIR
    try:
        root = SESSIONS_DIR.resolve()
        directory = root / ".creation_requests"
        path = directory / f"{UUID(str(request_id))}.json"
        if directory.resolve() != directory or path.resolve().parent != directory:
            raise PlanningError(409, "RECEIPT_CORRUPT", "Creation receipt storage is inconsistent.")
        return path
    except (OSError, RuntimeError) as error:
        raise PlanningError(503, "RECEIPT_STORAGE_UNAVAILABLE", "Creation receipt storage is unavailable.") from error


def read_receipt(request_id) -> CreationReceipt | None:
    path = receipt_path(request_id)
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_RECEIPT_BYTES + 1)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise PlanningError(503, "RECEIPT_STORAGE_UNAVAILABLE", "Creation receipt storage is unavailable.") from error
    try:
        if len(raw) > MAX_RECEIPT_BYTES:
            raise ValueError("Oversized receipt")
        data = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        receipt = CreationReceipt.model_validate(data)
        if (json.dumps(receipt.model_dump(mode="json"), sort_keys=True) != json.dumps(data, sort_keys=True)
                or str(receipt.client_request_id) != str(request_id)):
            raise ValueError("Receipt identity or shape mismatch")
        return receipt
    except (ValueError, TypeError, ValidationError, UnicodeError, RecursionError) as error:
        raise PlanningError(409, "RECEIPT_CORRUPT", "Creation receipt is damaged or incompatible. No replay is permitted.") from error


def write_receipt(receipt: CreationReceipt, *, initial=False):
    path = receipt_path(receipt.client_request_id)
    temporary = path.with_suffix(f".{uuid4()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if initial:
            if path.exists():
                raise PlanningError(409, "RECEIPT_CONFLICT", "A creation receipt already exists. Check its outcome.")
            # Count orphaned temporary files too; never evict uncertain operations.
            with os.scandir(path.parent) as entries:
                if sum(1 for _ in islice(entries, MAX_RECEIPTS)) >= MAX_RECEIPTS:
                    raise PlanningError(503, "RECEIPT_CAPACITY", "Creation receipt storage is full. No new creation was started.")
        raw = receipt.model_dump_json().encode("utf-8")
        if len(raw) > MAX_RECEIPT_BYTES:
            raise PlanningError(503, "RECEIPT_CAPACITY", "Creation receipt exceeds its storage bound.")
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise PlanningError(503, "RECEIPT_STORAGE_UNAVAILABLE", "Unable to record creation outcome. Check the request ID; do not blindly retry.") from error
    finally:
        # Only our exact disposable temporary file; never remove a published receipt.
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def confirmed_session(receipt: CreationReceipt):
    try:
        saved = get_saved_session(str(receipt.session_id))
    except PlanningError as error:
        if error.status == 503:
            raise
        raise PlanningError(409, "RECEIPT_INCONSISTENT", "Recorded creation has no compatible saved session. No replay is permitted.") from error
    if (saved.session.created_at != receipt.session_created_at
            or request_fingerprint(saved.session.plan.original_prompt, receipt.mode) != receipt.fingerprint):
        raise PlanningError(409, "RECEIPT_INCONSISTENT", "Creation receipt and saved session identities disagree. No replay is permitted.")
    return saved

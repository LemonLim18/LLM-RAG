"""One editable default document per verified original; no V9 runtime imports.

Mutation callers must hold the PlanningService gate. This is not cross-process CAS.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field, TypeAdapter
from .generated_originals import ArtifactId, Digest, OriginalMetadata, StrictModel, canonical, read_original
from .planning_service import PlanningError
from .saved_sessions import _reject_constant, _unique_object

MAX_CONTENT_BYTES = 1024 * 1024
MAX_RECORD_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 128
DocumentId = Annotated[str, Field(pattern=r'^working-[a-f0-9]{64}$')]


class OpenWorkingRequest(StrictModel):
    original_id: ArtifactId


class SaveWorkingRequest(StrictModel):
    expected_revision: UUID
    content: str = Field(strict=True, max_length=MAX_CONTENT_BYTES)


class WorkingMetadata(StrictModel):
    schema_version: Literal[1] = 1
    document_id: DocumentId
    original: OriginalMetadata
    revision: UUID
    save_sequence: int = Field(strict=True, ge=0)
    created_at: str
    updated_at: str
    content_sha256: Digest
    encoding: Literal['utf-8'] = 'utf-8'
    validation: Literal['unvalidated'] = 'unvalidated'
    deployment: Literal['not_deployed'] = 'not_deployed'


class WorkingDocument(WorkingMetadata):
    content: str = Field(strict=True)
    record_sha256: Digest


class OpenWorkingResponse(StrictModel):
    api_version: Literal[1] = 1
    outcome: Literal['created', 'reopened']
    document: WorkingDocument


class WorkingList(StrictModel):
    api_version: Literal[1] = 1
    limit: int = MAX_ENTRIES
    documents: list[WorkingMetadata]


def document_identity(original_id: str) -> str:
    TypeAdapter(ArtifactId).validate_python(original_id)
    return 'working-' + original_id.removeprefix('original-')


def storage_root() -> Path:
    from app.config import STORAGE_DIR
    root = STORAGE_DIR.resolve() / 'workbench' / 'working_documents'
    if root.parent.resolve() != root.parent or root.resolve() != root:
        raise PlanningError(409, 'INVALID_WORKING_STORAGE', 'Working storage must not be redirected.')
    return root


def _path(identity):
    try:
        TypeAdapter(DocumentId).validate_python(identity)
    except ValueError as error:
        raise PlanningError(422, 'INVALID_DOCUMENT_ID', 'A valid working document identity is required.') from error
    path = storage_root() / f'{identity}.json'
    if path.is_symlink() or path.resolve() != path:
        raise PlanningError(409, 'CORRUPT_WORKING_DOCUMENT', 'Working document storage is redirected.')
    return path


def _unavailable():
    return PlanningError(503, 'WORKING_STORAGE_UNAVAILABLE', 'Working storage could not confirm the operation. Inspect saved state before retrying; a write may have committed.')


def _content_bytes(content):
    try:
        raw = content.encode('utf-8')
    except UnicodeError as error:
        raise PlanningError(422, 'INVALID_TEXT_ENCODING', 'Content must be valid UTF-8 text.') from error
    if len(raw) > MAX_CONTENT_BYTES:
        raise PlanningError(413, 'WORKING_CONTENT_TOO_LARGE', 'Working content exceeds the 1 MiB UTF-8 limit.')
    return raw


def read_document(identity: str) -> WorkingDocument:
    try:
        with _path(identity).open('rb') as stream:
            raw = stream.read(MAX_RECORD_BYTES + 1)
        if len(raw) > MAX_RECORD_BYTES: raise ValueError('Oversized record')
        data = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        record = WorkingDocument.model_validate(data)
        encoded = record.model_dump(mode='json')
        if canonical(encoded) != canonical(data) or record.document_id != identity or document_identity(record.original.artifact_id) != identity:
            raise ValueError('Identity/schema mismatch')
        content = record.content.encode('utf-8')
        if len(content) > MAX_CONTENT_BYTES or sha256(content).hexdigest() != record.content_sha256:
            raise ValueError('Content mismatch')
        if sha256(canonical({k: v for k, v in encoded.items() if k != 'record_sha256'})).hexdigest() != record.record_sha256:
            raise ValueError('Record mismatch')
        for timestamp in (record.created_at, record.updated_at):
            if datetime.fromisoformat(timestamp).tzinfo is None: raise ValueError('Timestamp')
        return record
    except FileNotFoundError as error:
        raise PlanningError(404, 'WORKING_DOCUMENT_NOT_FOUND', 'The working document does not exist.') from error
    except OSError as error:
        raise _unavailable() from error
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise PlanningError(409, 'CORRUPT_WORKING_DOCUMENT', 'Working document failed integrity verification. It was not repaired.') from error


def _entries():
    root = storage_root()
    if not root.exists(): return []
    names = []
    with os.scandir(root) as entries:
        for entry in entries:
            names.append(entry.name)
            if len(names) > MAX_ENTRIES:
                raise PlanningError(503, 'WORKING_CAPACITY', 'Working storage capacity exceeded. No files were removed.')
    return sorted(names)


def list_documents() -> WorkingList:
    try:
        result = []
        for name in _entries():
            if name.endswith('.tmp'): continue
            if not re.fullmatch(r'working-[a-f0-9]{64}\.json', name):
                raise PlanningError(409, 'CORRUPT_WORKING_DOCUMENT', 'Working storage contains an unsupported record.')
            record = read_document(name[:-5])
            result.append(WorkingMetadata.model_validate(record.model_dump(exclude={'content', 'record_sha256'})))
        return WorkingList(documents=result)
    except OSError as error:
        raise _unavailable() from error


def _publish(unsigned: dict, *, expected_revision: UUID | None) -> WorkingDocument:
    temporary = None
    try:
        path = _path(unsigned['document_id'])
        if expected_revision is None and len(_entries()) >= MAX_ENTRIES:
            raise PlanningError(503, 'WORKING_CAPACITY', 'Working storage is full. No documents were evicted.')
        record = WorkingDocument(**unsigned, record_sha256=sha256(canonical(unsigned)).hexdigest())
        raw = canonical(record.model_dump(mode='json'))
        if len(raw) > MAX_RECORD_BYTES:
            raise PlanningError(413, 'WORKING_CONTENT_TOO_LARGE', 'Working record is too large.')
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.parent / f'{uuid4().hex}.tmp'
        with temporary.open('xb') as stream:
            if stream.write(raw) != len(raw): raise OSError('Partial write')
            stream.flush()
            os.fsync(stream.fileno())
        if expected_revision is None:
            try: os.link(temporary, path)
            except FileExistsError:
                existing = read_document(record.document_id)
                if existing.original != record.original:
                    raise PlanningError(409, 'WORKING_IDENTITY_CONFLICT', 'The existing working document belongs to a different original.')
                return existing
        else:
            # Detect an external change before replace, without claiming cross-process CAS.
            if read_document(record.document_id).revision != expected_revision:
                raise PlanningError(409, 'STALE_WORKING_REVISION', 'Saved working state changed. Inspect it before saving again.')
            os.replace(temporary, path)
        return read_document(record.document_id)
    except OSError as error:
        raise _unavailable() from error
    except (ValueError, TypeError, RecursionError) as error:
        raise PlanningError(409, 'INVALID_WORKING_RECORD', 'Working document could not be serialized safely.') from error
    finally:
        if temporary is not None:
            try: temporary.unlink(missing_ok=True)
            except OSError: pass


def open_document(request: OpenWorkingRequest) -> OpenWorkingResponse:
    original = read_original(request.original_id)
    metadata = OriginalMetadata.model_validate(original.model_dump(exclude={'configuration', 'record_sha256'}))
    identity = document_identity(original.artifact_id)
    try:
        if _path(identity).exists():
            existing = read_document(identity)
            if existing.original != metadata:
                raise PlanningError(409, 'WORKING_IDENTITY_CONFLICT', 'The working document does not match its verified original.')
            return OpenWorkingResponse(outcome='reopened', document=existing)
        content = _content_bytes(original.configuration)
        now = datetime.now(timezone.utc).isoformat()
        unsigned = WorkingMetadata(document_id=identity, original=metadata, revision=uuid4(), save_sequence=0,
                                   created_at=now, updated_at=now, content_sha256=sha256(content).hexdigest()).model_dump(mode='json')
        record = _publish({**unsigned, 'content': original.configuration}, expected_revision=None)
        return OpenWorkingResponse(outcome='created' if str(record.revision) == unsigned['revision'] else 'reopened', document=record)
    except OSError as error:
        raise _unavailable() from error


def save_document(identity: str, request: SaveWorkingRequest) -> WorkingDocument:
    current = read_document(identity)
    if current.revision != request.expected_revision:
        raise PlanningError(409, 'STALE_WORKING_REVISION', 'Saved working state changed. Your text was not saved; inspect the current revision.')
    content = _content_bytes(request.content)
    unsigned = current.model_dump(mode='json', exclude={'record_sha256'})
    unsigned.update(content=request.content, content_sha256=sha256(content).hexdigest(), revision=str(uuid4()),
                    save_sequence=current.save_sequence + 1, updated_at=datetime.now(timezone.utc).isoformat())
    return _publish(unsigned, expected_revision=current.revision)

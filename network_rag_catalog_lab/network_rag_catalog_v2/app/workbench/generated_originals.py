"""Explicit immutable capture of verified saved-session output. No AI imports."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import re
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .planning_service import PlanningError
from .saved_sessions import _reject_constant, _unique_object, get_saved_session

MAX_RECORD_BYTES = 2 * 1024 * 1024
MAX_ENTRIES = 128
Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
ArtifactId = Annotated[str, Field(pattern=r'^original-[a-f0-9]{64}$')]
Identity = Annotated[str, Field(strict=True, min_length=1, max_length=512)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CaptureRequest(StrictModel):
    session_id: UUID
    expected_session_revision: Digest
    task_id: Identity
    device_id: Identity
    config_index: int = Field(strict=True, ge=0)


class OriginalSource(StrictModel):
    session_id: UUID
    session_revision: Digest
    task_id: Identity
    device_id: Identity
    config_index: int = Field(strict=True, ge=0)


class OriginalMetadata(StrictModel):
    schema_version: Literal[1] = 1
    kind: Literal['generated_original'] = 'generated_original'
    artifact_id: ArtifactId
    source: OriginalSource
    logical_intent_id: str | None
    operation_id: str | None
    category: str | None
    hostname: str | None
    vendor: str | None
    platform: str | None
    version: str | None
    captured_at: str
    content_sha256: Digest
    content_encoding: Literal['utf-8'] = 'utf-8'
    # Only explicit recorded provenance. No live validation or inventory lookup.
    authority: dict[str, str | None]
    validity: Literal['historical_not_checked'] = 'historical_not_checked'


class GeneratedOriginal(OriginalMetadata):
    configuration: str = Field(strict=True, min_length=1)
    record_sha256: Digest


class CaptureResponse(StrictModel):
    api_version: Literal[1] = 1
    outcome: Literal['created', 'already_saved']
    artifact: GeneratedOriginal


class OriginalList(StrictModel):
    api_version: Literal[1] = 1
    limit: int = MAX_ENTRIES
    artifacts: list[OriginalMetadata]


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def artifact_identity(source: OriginalSource) -> str:
    return 'original-' + sha256(canonical({'schema_version': 1, 'source': source.model_dump(mode='json')})).hexdigest()


def storage_root() -> Path:
    from app.config import STORAGE_DIR
    base = STORAGE_DIR.resolve()
    root = base / 'workbench' / 'generated_originals'
    if root.parent.resolve() != root.parent or root.resolve() != root:
        raise PlanningError(409, 'INVALID_ARTIFACT_STORAGE', 'Original storage must not be redirected.')
    return root


def _path(identity: str) -> Path:
    # Also validate callers which do not enter through FastAPI.
    from pydantic import TypeAdapter
    try:
        TypeAdapter(ArtifactId).validate_python(identity)
    except ValueError as error:
        raise PlanningError(422, 'INVALID_ARTIFACT_ID', 'A valid original identity is required.') from error
    root = storage_root()
    path = root / f'{identity}.json'
    if path.is_symlink() or path.resolve() != path:
        raise PlanningError(409, 'CORRUPT_ARTIFACT', 'Original storage is redirected or inconsistent.')
    return path


def _storage_error(error):
    return PlanningError(503, 'ARTIFACT_STORAGE_UNAVAILABLE', 'Original storage is unavailable. If a capture was submitted, refresh Saved Originals to inspect its outcome; do not retry blindly.')


def read_original(identity: str) -> GeneratedOriginal:
    try:
        path = _path(identity)
        with path.open('rb') as stream:
            raw = stream.read(MAX_RECORD_BYTES + 1)
        if len(raw) > MAX_RECORD_BYTES:
            raise ValueError('Oversize')
        data = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        record = GeneratedOriginal.model_validate(data)
        encoded = record.model_dump(mode='json')
        if canonical(encoded) != canonical(data) or record.artifact_id != identity or artifact_identity(record.source) != identity:
            raise ValueError('Identity or schema mismatch')
        if sha256(record.configuration.encode('utf-8')).hexdigest() != record.content_sha256:
            raise ValueError('Content mismatch')
        unsigned = {key: value for key, value in encoded.items() if key != 'record_sha256'}
        if sha256(canonical(unsigned)).hexdigest() != record.record_sha256:
            raise ValueError('Record mismatch')
        timestamp = datetime.fromisoformat(record.captured_at)
        if timestamp.tzinfo is None:
            raise ValueError('Timestamp lacks timezone')
        return record
    except FileNotFoundError as error:
        raise PlanningError(404, 'ARTIFACT_NOT_FOUND', 'The saved original does not exist.') from error
    except OSError as error:
        raise _storage_error(error) from error
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise PlanningError(409, 'CORRUPT_ARTIFACT', 'The saved original failed schema, identity or integrity verification. It was not repaired.') from error


def _entries(root: Path):
    if not root.exists():
        return []
    entries = []
    with os.scandir(root) as scan:
        for entry in scan:
            entries.append(entry.name)
            if len(entries) > MAX_ENTRIES:
                raise PlanningError(503, 'ARTIFACT_CAPACITY', 'Original storage exceeds the supported bounded collection size. No records were removed.')
    return sorted(entries)


def list_originals() -> OriginalList:
    try:
        names = _entries(storage_root())
        result = []
        for name in names:
            if name.endswith('.tmp'):
                continue  # Unpublished crash remnants; counted toward capacity, never returned.
            if not re.fullmatch(r'original-[a-f0-9]{64}\.json', name):
                raise PlanningError(409, 'CORRUPT_ARTIFACT', 'Original storage contains an unsupported entry.')
            original = read_original(name[:-5])
            result.append(OriginalMetadata.model_validate(original.model_dump(exclude={'configuration', 'record_sha256'})))
        return OriginalList(artifacts=result)
    except OSError as error:
        raise _storage_error(error) from error


def _optional(record: dict, key: str):
    value = record.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError('Invalid metadata')
    return value


def capture_original(request: CaptureRequest) -> CaptureResponse:
    """Called under PlanningService's shared process mutation gate."""
    saved = get_saved_session(str(request.session_id))
    if saved.session_revision != request.expected_session_revision:
        raise PlanningError(409, 'STALE_SOURCE_SESSION', 'The saved session revision changed. Review the current saved state before capturing.')
    source = OriginalSource(session_id=request.session_id, session_revision=saved.session_revision,
                            task_id=request.task_id, device_id=request.device_id, config_index=request.config_index)
    try:
        matches = [task for task in saved.session.plan.tasks if task.intent_id == request.task_id]
        if len(matches) != 1:
            raise ValueError('Unknown/ambiguous task')
        task = matches[0]
        if request.config_index >= len(task.configs):
            raise ValueError('Unknown entry')
        config = task.configs[request.config_index]
        targets = [item for item in task.target_devices if item.get('id') == request.device_id]
        if len(targets) != 1 or config.get('device_id') != request.device_id or (task.device_id and task.device_id != request.device_id):
            raise ValueError('Inconsistent device')
        content = config.get('configuration')
        if not isinstance(content, str) or not content:
            raise ValueError('Missing text')
        metadata = {key: _optional(config, key) for key in ('hostname', 'vendor', 'platform', 'version')}
        target_metadata = {key: _optional(targets[0], key) for key in metadata}
        if any(value is not None and target_metadata[key] is not None and value != target_metadata[key] for key, value in metadata.items()):
            raise ValueError('Conflicting metadata')
        metadata = {key: value if value is not None else target_metadata[key] for key, value in metadata.items()}
        plan = saved.session.plan
        authority = {f'{scope}_{field}': getattr(obj, field, None) for scope, obj in [('plan', plan), ('task', task)]
                     for field in ('runtime_authority', 'knowledge_snapshot_id', 'source_revision', 'context_revision')}
        stable = dict(schema_version=1, kind='generated_original', artifact_id=artifact_identity(source), source=source.model_dump(mode='json'),
                      logical_intent_id=task.logical_intent_id or None, operation_id=task.operation_id or None, category=task.category or None,
                      **metadata, content_encoding='utf-8', content_sha256=sha256(content.encode('utf-8')).hexdigest(),
                      configuration=content, authority=authority, validity='historical_not_checked')
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise PlanningError(409, 'SOURCE_ASSOCIATION_ERROR', 'The selected configuration has missing, ambiguous or inconsistent task/device provenance.') from error

    temporary = None
    try:
        path = _path(stable['artifact_id'])
        if path.exists():
            return _existing(stable)
        root = path.parent
        if len(_entries(root)) >= MAX_ENTRIES:
            raise PlanningError(503, 'ARTIFACT_CAPACITY', 'Saved original capacity reached. No records were overwritten or evicted.')
        root.mkdir(parents=True, exist_ok=True)
        unsigned = {**stable, 'captured_at': datetime.now(timezone.utc).isoformat()}
        record = GeneratedOriginal(**unsigned, record_sha256=sha256(canonical(unsigned)).hexdigest())
        raw = canonical(record.model_dump(mode='json'))
        if len(raw) > MAX_RECORD_BYTES:
            raise PlanningError(413, 'ARTIFACT_TOO_LARGE', 'This original exceeds the supported record size.')
        temporary = root / f'{uuid4().hex}.tmp'
        with temporary.open('xb') as stream:
            if stream.write(raw) != len(raw):
                raise OSError('Incomplete write')
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic no-clobber publication on local NTFS. Unlike os.replace, a
        # competing/preexisting destination cannot be overwritten. No fallback.
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _existing(stable)
        verified = read_original(record.artifact_id)
        return CaptureResponse(outcome='created', artifact=verified)
    except OSError as error:
        raise _storage_error(error) from error
    except (ValueError, TypeError, RecursionError) as error:
        raise PlanningError(409, 'INVALID_ORIGINAL', 'The original could not be safely serialized. No replacement was performed.') from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _existing(stable: dict) -> CaptureResponse:
    original = read_original(stable['artifact_id'])
    if original.model_dump(mode='json', exclude={'captured_at', 'record_sha256'}) != stable:
        raise PlanningError(409, 'ARTIFACT_IDENTITY_CONFLICT', 'The stored original does not match the verified source. Nothing was replaced.')
    return CaptureResponse(outcome='already_saved', artifact=original)

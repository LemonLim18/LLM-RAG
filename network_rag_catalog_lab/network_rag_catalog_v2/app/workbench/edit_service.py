"""Read / interpret outside the mutation gate / recheck. No persistence."""
from hashlib import sha256
from threading import Lock
from uuid import uuid4
from .edit_models import EditRequest, EditResponse
from .generated_originals import OriginalMetadata, read_original
from .working_documents import read_document
from .planning_service import PlanningError
from .inventory_service import _revision


def reject(code, message, status=409):
    raise PlanningError(status, code, message)


class EditService:
    def __init__(self, planning):
        self.planning = planning
        self.busy = Lock()

    def _document(self, identity, revision):
        doc = read_document(identity)
        if doc.revision != revision:
            reject('STALE_WORKING_REVISION', 'Saved working revision changed. Inspect saved state before requesting another edit.')
        original = read_original(doc.original.artifact_id)
        metadata = OriginalMetadata.model_validate(original.model_dump(include=set(OriginalMetadata.model_fields)))
        if metadata != doc.original:
            reject('SOURCE_ASSOCIATION_ERROR', 'The working file and verified original no longer agree.')
        return doc

    def propose(self, identity: str, request: EditRequest) -> EditResponse:
        try:
            encoded = request.current_content.encode('utf-8')
        except UnicodeError:
            reject('INVALID_EDIT_TEXT', 'Current buffer must be valid UTF-8.', 422)
        if len(encoded) > 65536 or not request.instruction.strip():
            reject('INVALID_EDIT_INPUT', 'Use a nonempty instruction and a buffer of at most 64 KiB UTF-8.', 422)
        if not self.busy.acquire(blocking=False):
            reject('EDIT_BUSY', 'An edit interpretation is already running. No second inference was started.', 503)
        try:
            return self._propose(identity, request, encoded)
        except PlanningError:
            raise
        except Exception:
            # Never expose local paths, raw model text or upstream errors.
            reject('EDIT_CONTEXT_UNAVAILABLE', 'V9 knowledge, device context or document storage could not be verified.', 503)
        finally:
            self.busy.release()

    def _propose(self, identity, request, encoded):
        from app import document_edits as edits
        from app.catalog import get_operation, reload_catalog
        from app.context import source_revision
        from app.devices.inventory import load_inventory, find_explicit_target_references
        from app.devices.context_validator import validate_device_context
        from app.devices.target_query import parse_description
        from app.devices.target_resolver import resolve_queries
        from app.knowledge.runtime import snapshot_scope, current_snapshot
        from app.parameters.schema_loader import load_schema
        from app.parameters.validator import validate_parameter_result
        from app.config import OLLAMA_LLM_MODEL, runtime_mode

        def prepare():
            doc = self._document(identity, request.expected_revision)
            inventory = load_inventory()
            matches = [d for d in inventory if d['id'] == doc.original.source.device_id]
            if len(matches) != 1:
                reject('EDIT_TARGET_UNAVAILABLE', 'The source device is missing or ambiguous in current V9 inventory.')
            device = matches[0]
            if any(getattr(doc.original, k) != device.get(k) for k in ('hostname', 'vendor', 'platform', 'version')):
                reject('EDIT_DEVICE_CHANGED', 'Recorded device identity/platform differs from current inventory; no edit is proposed.')
            if device['vendor'] != 'cisco' or device['platform'] != 'iosxe' or doc.original.category != 'vlan':
                reject('UNSUPPORTED_EDIT_CONTEXT', 'This bounded editor supports Cisco IOS XE VLAN-source documents only.', 422)
            reload_catalog()
            snapshot = current_snapshot()
            with snapshot_scope(snapshot):
                source_operation = get_operation(doc.original.operation_id)
                if source_operation['category_id'] != doc.original.category:
                    reject('SOURCE_ASSOCIATION_ERROR', 'Recorded source operation/category no longer agrees with V9 knowledge.')
                operation = get_operation('rename_vlan')
                if operation.get('status', 'active') != 'active' or operation['category_id'] != 'vlan':
                    reject('UNSUPPORTED_EDIT_CONTEXT', 'The active catalog does not support this edit.', 422)
                schema = load_schema('rename_vlan', [device])
                revision = source_revision()
            refs = find_explicit_target_references(request.instruction, inventory)
            if any(ref != device['hostname'] for ref in refs):
                reject('EDIT_TARGET_CONFLICT', 'Instruction targets another device. This edit is restricted to the active file.', 422)
            return doc, device, inventory, snapshot, schema, revision

        doc, device, inventory, snapshot, schema, revision = self.planning.mutate_working_document(prepare)
        try:
            interpretation = edits.interpret(request.instruction, schema, device, request.current_content)
        except ValueError:
            reject('INVALID_MODEL_RESPONSE', 'Local V9 returned an invalid structured edit interpretation. No proposal was staged.', 502)
        except Exception:
            reject('LOCAL_MODEL_UNAVAILABLE', 'The configured local model failed or timed out. No mock response was substituted.', 503)

        def finish():
            self._document(identity, request.expected_revision)
            with snapshot_scope(snapshot):
                if runtime_mode() != ('published' if snapshot else 'files') or source_revision() != revision or _revision(load_inventory()) != _revision(inventory):
                    reject('EDIT_SOURCE_CHANGED', 'Knowledge or inventory changed during inference. Request a new proposal.')
                response = dict(document_id=identity, base_revision=doc.revision,
                    base_content_sha256=sha256(encoded).hexdigest(), proposal_id=uuid4(),
                    authority={'runtime': 'published_release' if snapshot else 'direct_files',
                               'release_id': snapshot.release_id if snapshot else None,
                               'source_revision': revision, 'model': OLLAMA_LLM_MODEL,
                               'knowledge_lookup': 'exact_catalog_operation', 'retrieval': 'not_used'},
                    outcome='unsupported', message='Only one existing VLAN name change is supported in this iteration.')
                if interpretation.outcome == 'unsupported':
                    return EditResponse(**response)
                if interpretation.target:
                    if interpretation.target not in request.instruction:
                        reject('UNGROUNDED_EDIT', 'Model target is not grounded in the instruction.', 422)
                    resolved = resolve_queries([parse_description(interpretation.target, inventory)], inventory)
                    if resolved['issues'] or [d['id'] for d in resolved['devices']] != [device['id']]:
                        reject('EDIT_TARGET_CONFLICT', 'Requested target does not uniquely match this working file.', 422)
                params = {k: getattr(interpretation, k) for k in ('vlan_id', 'new_vlan_name') if getattr(interpretation, k) is not None}
                validation = validate_parameter_result(params, schema)
                if interpretation.outcome == 'clarification_required' or any(i.type == 'MISSING' for i in validation.issues):
                    return EditResponse(**{**response, 'outcome': 'clarification_required',
                        'message': 'State the existing VLAN ID and its new name in a new instruction. No clarification session or edit was created.'})
                if interpretation.operation_id != 'rename_vlan' or not validation.valid:
                    reject('INVALID_EDIT_PARAMETERS', 'Interpreted parameters do not satisfy the V9 rename_vlan schema.', 422)
                if not all(edits.literal(value, request.instruction) for value in params.values()):
                    reject('UNGROUNDED_EDIT', 'Model parameters were not explicitly present in the instruction.', 422)
                if validate_device_context('rename_vlan', 'vlan', params, [device]):
                    reject('EDIT_VENDOR_VALIDATION', 'V9 device capability/policy rejects this operation.', 422)
                try:
                    proposed, old = edits.proposed_text(request.current_content, params, device)
                except ValueError:
                    reject('EDIT_BLOCK_UNSUPPORTED', 'Expected one unambiguous existing VLAN/name block and a compatible V9 template. No content was changed.', 422)
                if interpretation.current_vlan_name is not None and (old != interpretation.current_vlan_name or not edits.literal(old, request.instruction)):
                    reject('EDIT_OLD_VALUE_CONFLICT', 'The requested old name does not match the current accepted buffer.', 422)
                if source_revision() != revision:
                    reject('EDIT_SOURCE_CHANGED', 'Source changed during validation.')
                return EditResponse(**{**response, 'outcome': 'no_change' if proposed == request.current_content else 'proposal',
                    'message': 'V9 interpreted and validated one VLAN rename. Review before accepting; the rest of this historical document is unvalidated.',
                    'proposed_content': proposed, 'parameters': params,
                    'evidence': {'vlan_id': 'explicit instruction', 'new_vlan_name': 'explicit instruction',
                                 'old_name': old, 'device_id': device['id'], 'original_id': doc.original.artifact_id}})
        return self.planning.mutate_working_document(finish)

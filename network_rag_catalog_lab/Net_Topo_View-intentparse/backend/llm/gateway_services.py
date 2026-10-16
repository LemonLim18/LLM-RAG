"""Narrow local services shared by both assistants. No remote fallback imports."""
import json
from uuid import uuid4

from pydantic import Field
from llm.gateway_models import Evidence, StrictModel, ToolResult, TurnRequest, text_digest
from llm.tools import Capability, ToolRegistry


class InventoryQuery(StrictModel):
    device_id: str | None = None


class GenerationRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=20000)
    model: str | None = None
    output_kind: str = Field(default='native', pattern='^(native|playbook)$')
    params: dict = Field(default_factory=dict)
    hosts: list[str] = Field(default_factory=list, max_length=1)


class DocumentProposalRequest(StrictModel):
    turn: TurnRequest


def inventory_snapshot(db, device_id=None):
    # Select only authorized descriptive fields, never credential columns.
    with db._connect() as c:
        devices = [dict(r) for r in c.execute('SELECT id,hostname,management_ip,vendor,model,os_version,role,status,site,location,aliases_json,engineering_facts_json FROM devices ORDER BY id')]
        interfaces = [dict(r) for r in c.execute('SELECT id,device_id,name,interface_type,ip_address FROM interfaces ORDER BY id')]
        links = [dict(r) for r in c.execute('SELECT id,src_device_id,src_interface_id,dst_device_id,dst_interface_id FROM links ORDER BY id')]
    if device_id is not None:
        devices = [d for d in devices if str(d['id']) == device_id or d['hostname'].casefold() == device_id.casefold()]
    for device in devices:
        from llm.gateway_inventory import facts_revision
        device['aliases'] = json.loads(device.pop('aliases_json'))
        device['engineering_facts'] = json.loads(device.pop('engineering_facts_json'))
        device['engineering_facts_revision'] = facts_revision(device['engineering_facts'])
        device['interfaces'] = [i for i in interfaces if i['device_id'] == device['id']]
    ids = {d['id'] for d in devices}
    return {'devices': devices, 'links': [l for l in links if l['src_device_id'] in ids or l['dst_device_id'] in ids],
            'structure_source': 'stored_inventory', 'reachability': 'not_measured', 'live_state_available': False}


def registry_for(db):
    registry = ToolRegistry(require_authorization=True)
    def inventory(params, authorization):
        """Read local stored inventory; this does not establish device reachability."""
        data = inventory_snapshot(db, params.device_id)
        from datetime import datetime, timezone
        return ToolResult(status='success', data=data, evidence=[Evidence(
            id=uuid4().hex, source='sqlite.inventory', origin='stored', time_scope='current',
            retrieved_at=datetime.now(timezone.utc).isoformat(), freshness='not_applicable',
            source_revision=text_digest(json.dumps(data, sort_keys=True)),
            device_refs=[str(d['id']) for d in data['devices']], authority='inventory')])
    registry.register_capability('inventory.read', inventory, Capability(InventoryQuery, ToolResult, 'read',
        frozenset({'floating', 'studio'}), frozenset({'admin', 'engineer', 'auditor'}),
        resource_scopes=frozenset({'inventory.local'}),required_permissions=frozenset({'network.inventory.read'})))
    async def generation(params, authorization):
        from llm.gateway_store import ConversationStore
        from llm.gateway_v9 import preview
        ConversationStore(db).get(authorization.conversation_id, authorization.principal, 'studio')
        user = {'username': authorization.principal, 'role': authorization.role}
        result = await preview(db, user, params.prompt, params.model, params.output_kind, params.params, params.hosts)
        release=result['parsed_intent'].get('knowledge_snapshot_id')
        references=[Evidence(id=uuid4().hex,source='V9 published knowledge',origin='stored',authority='published_operation',source_revision=release)]
        return ToolResult(status='success', data=result, evidence=references)
    async def document_proposal(params, authorization):
        from llm.gateway_store import ConversationStore
        from llm.gateway_documents import build_context, propose_edit
        ConversationStore(db).get(authorization.conversation_id, authorization.principal, 'studio')
        user = {'username': authorization.principal, 'role': authorization.role}
        context, evidence, coverage = build_context(db, authorization.conversation_id, user, params.turn)
        proposal, model = await propose_edit(db, user, params.turn, context, ConversationStore(db).history(authorization.conversation_id,user)[-6:])
        return ToolResult(status='success', data={'proposal': proposal, 'model': model, 'coverage': coverage}, evidence=evidence)
    for name, fn, inputs in [('v9.preview', generation, GenerationRequest),
                             ('document.propose', document_proposal, DocumentProposalRequest)]:
        registry.register_capability(name, fn, Capability(inputs, ToolResult, 'propose',
            frozenset({'studio'}), frozenset({'admin', 'engineer'}), timeout=210,
            resource_scopes=frozenset({'conversation.owned','workspace.authorized' if name=='document.propose' else 'knowledge.published'}),
            required_permissions=frozenset({'engineering.propose'})))
    from llm.gateway_network import NetworkReader, NetworkQuery
    reader=NetworkReader(db)
    for domain in ['topology','telemetry','syslog','incidents','configuration','knowledge']:
        name='knowledge.search' if domain=='knowledge' else 'network.'+domain
        def read(params, authorization, selected=domain):
            return reader.read(selected,params,authorization)
        registry.register_capability(name,read,Capability(NetworkQuery,ToolResult,'read',
            frozenset({'floating','studio'}),frozenset({'admin','engineer','auditor'}),
            resource_scopes=frozenset({'network.local.read'}),required_permissions=frozenset({'network.inventory.read'})))
    return registry

"""Ephemeral Studio context and engineering coordination; no editor/write authority."""
import difflib
import re
from fastapi import HTTPException
from llm.gateway_models import text_digest
from llm.gateway_routing import SemanticRoute


def editor_reference(editor):
    if not editor:return {}
    return {key:getattr(editor,key) for key in ['document_id','path','model_id','model_version','buffer_epoch','saved_revision','language','is_dirty']} | {'digest':text_digest(editor.content)}


def previous_engineering(service,identity,user,memory,previous):
    reference=memory.engineering_request_ref
    result=service.store.result_for(identity,user['username'],reference) if reference else previous
    if not result or result.get('kind') not in {'edit_proposal','generation_preview'}:return None
    role=result.get('context_coverage',{}).get('authorization_role')
    from auth.auth import normalize_role
    if role and role!=normalize_role(user.get('role')):return None
    return result


def contextual_studio_route(prompt,editor,previous):
    """Resolve explicit proposal follow-ups before general model classification.

    No operation catalog is interpreted here. V9 receives generation requests.
    """
    from llm.gateway_documents import editor_selection_question,editor_rename_question,editor_issue_question
    if question:=editor_selection_question(prompt,editor):
        return SemanticRoute(intent='clarify',question=question,use_editor=True,planning={'editor_selection_required':True})
    if question:=editor_rename_question(prompt,editor):
        return SemanticRoute(intent='clarify',question=question,use_editor=True,planning={'editor_rename_required':True})
    if question:=editor_issue_question(prompt,editor):
        return SemanticRoute(intent='clarify',question=question,use_editor=True,planning={'editor_correction_required':True})
    # The existing exact-literal proposal needs no inference to identify an
    # explicit editor request. Keep it usable when Ollama is unavailable; this
    # selects a reviewed proposal, never applies or saves its patch.
    from llm.gateway_references import read_intent_text
    effect_text=read_intent_text(prompt)
    editor_reference=re.search(r'\b(active file|open file|current file|editor|buffer|selected code)\b',effect_text,re.I)
    editor_reference=editor_reference or re.search(r'\bpropose\b.{0,40}\b(?:active|current|open|unsaved)\b',effect_text,re.I)
    if editor and editor_reference and not re.search(r'\b(explain|why|without (?:changing|modifying|editing))\b',effect_text,re.I):
        from types import SimpleNamespace
        from llm.gateway_documents import literal_address_patch
        if literal_address_patch(SimpleNamespace(prompt=prompt,editor=editor), (previous or {}).get('proposal')):
            return SemanticRoute(intent='edit',use_editor=True,use_history=bool(previous))
    if not previous:return None
    if previous.get('kind')=='generation_preview' and re.search(r'\b(sorry|meant|instead|set its|change (?:its|the|that)|remote AS|that interface|task \d|operation \d)\b',prompt,re.I) and not re.search(r'\b(why|explain|what is|do not|don.t)\b',prompt,re.I):
        kind=(previous.get('preview') or {}).get('output_kind','native')
        return SemanticRoute(intent='generate_playbook' if kind=='playbook' else 'generate_native',use_history=True)
    proposal=previous.get('proposal')
    linked=proposal and editor and proposal['document_id']==editor.document_id and proposal['path']==editor.path
    explanation=bool(re.search(r'\b(explain|why|what|describe)\b',prompt,re.I) and re.search(r'\b(modification|proposal|proposed|your change|you change|that change|previous change)\b',prompt,re.I))
    if explanation and proposal:
        if not linked:return SemanticRoute(intent='clarify',question='Open the document associated with that proposal so I can compare it with the current buffer.')
        return SemanticRoute(intent='explain',use_editor=True,use_history=True)
    if linked and re.search(r'\b(instead|keep (?:the )?original|that address|that parameter|your change|previous modification)\b',prompt,re.I):
        if re.search(r'\b(change|replace|modify|keep|use|make|set|correct)\b',prompt,re.I) and not re.search(r'\b(why|explain|do not|don.t)\b',prompt,re.I):
            return SemanticRoute(intent='edit',use_editor=True,use_history=True)
    return None


def proposal_explanation(previous,editor,related_editors=()):
    proposal=(previous or {}).get('proposal')
    if not proposal or not editor or proposal['document_id']!=editor.document_id or proposal['path']!=editor.path:return ''
    if proposal.get('files'):
        current={s.path:s for s in [editor,*related_editors]};parts=[]
        for file in proposal['files']:
            now=current.get(file['path'])
            status='Current buffer was not supplied; acceptance cannot be established.' if not now else 'Current buffer matches the original; this change remains proposed.' if now.content==file['original'] else 'Current buffer matches the proposed text; saving is a separate action and is not established.' if now.content==file['suggested'] else 'Current buffer differs from both versions; reconcile it before another edit.'
            diff=''.join(difflib.unified_diff(file['original'].splitlines(keepends=True),file['suggested'].splitlines(keepends=True),fromfile=file['path']+' (original)',tofile=file['path']+' (proposed)',n=2))[:6000]
            parts.append('**`'+file['path']+'`**\n\n'+status+'\n\n```diff\n'+diff+'\n```')
        return '\n\n'.join(parts)+'\n\nNo additional modification was proposed or saved by this explanation.'
    if editor.content==proposal['original']:state='The current buffer still matches the original. These changes remain a proposal.'
    elif editor.content==proposal['suggested']:state='The current buffer matches the proposed text. Acceptance and saving are separate actions; I cannot infer that it was saved.'
    else:state='The current buffer has changed since this proposal. This explanation describes the previous proposal; a new edit must use the current buffer.'
    diff=''.join(difflib.unified_diff(proposal['original'].splitlines(keepends=True),proposal['suggested'].splitlines(keepends=True),fromfile='original',tofile='proposed',n=2))[:12000]
    return state+'\n\nThe proposed differences are:\n\n```diff\n'+diff+'\n```\n\nNo additional modification was proposed or saved by this explanation.'


def validate_proposal(result,body):
    if result.status!='success':raise HTTPException(503,'Engineering service did not produce a reviewable result')
    proposal=result.data.get('proposal') or {};editor=body.editor
    if not editor or any(proposal.get(k)!=getattr(editor,k) for k in ['document_id','path','model_id','model_version','buffer_epoch','saved_revision']):
        raise HTTPException(409,'Proposal no longer matches the supplied editor identity and revision')
    if proposal.get('original')!=editor.content or proposal.get('base_digest')!=text_digest(editor.content):
        raise HTTPException(409,'Proposal exact base did not match the current buffer')
    files=proposal.get('files',[])
    if files:
        supplied={s.path:s for s in [editor,*body.related_editors]};seen=set()
        for item in files:
            snapshot=supplied.get(item.get('path'))
            if not snapshot or item['path'] in seen or snapshot.read_only:
                raise HTTPException(409,'Coordinated proposal is outside the supplied editable workspace')
            seen.add(item['path'])
            if any(item.get(k)!=getattr(snapshot,k) for k in ['document_id','model_id','model_version','buffer_epoch','saved_revision']):
                raise HTTPException(409,'Coordinated proposal document identity/revision changed')
            if item.get('original')!=snapshot.content or item.get('base_digest')!=text_digest(snapshot.content):
                raise HTTPException(409,'Coordinated proposal exact base does not match')
            if not isinstance(item.get('suggested'),str) or item['suggested']==snapshot.content:
                raise HTTPException(422,'Coordinated proposal includes an unchanged or invalid file')
    if not isinstance(proposal.get('suggested'),str) or not files and proposal['suggested']==editor.content:
        from llm.gateway_workspace import WorkspaceProposalFailure
        raise WorkspaceProposalFailure('No changes were proposed; the current buffer was preserved', {
            'scope':'proposal_effect_validation','proposal':proposal,
            'supplied_paths':[snapshot.path for snapshot in [editor,*body.related_editors]],
            'applied':False,'saved':False})
    literals=re.findall(r'\b(?:to|with)\s+((?:\d{1,3}\.){3}\d{1,3})\b',body.prompt,re.I)
    proposed_text='\n'.join(item['suggested'] for item in files) if files else proposal['suggested']
    original_text='\n'.join(item['original'] for item in files) if files else editor.content
    if literals and literals[-1] not in original_text and literals[-1] not in proposed_text:
        raise HTTPException(422,'The proposal missed the explicitly requested address; the current buffer was preserved')


def router_sections(documents, path):
    """Literal CLI stanza boundaries, not operation recognition or validation."""
    sections=[]
    for document in documents:
        if document.get('source')!=path or 'text' not in document:continue
        current=None
        for number,line in enumerate(document['text'].splitlines(),document.get('start_line',1)):
            heading=re.fullmatch(r'router\s+(ospf|bgp)\s+(.+)',line,re.I)
            if heading:
                current={'protocol':heading[1].upper(),'heading':line,'start':number,'end':number,'commands':[]}
                sections.append(current)
            elif current and line[:1].isspace() and line.strip():
                current['commands'].append(line.strip());current['end']=number
            elif line.strip():current=None
    return sections


def comment_only_request(question):
    """A narrow context focus, never an intent/permission or operation decision.

    Compound configuration questions retain the full active buffer.
    """
    if re.search(r'\b(?:OSPF|BGP|router.?id|neighbou?r|routing stanzas?|interface address)\b|\b(?:and|also)\b.{0,40}\b(?:configuration|code|routing|stanzas?|commands?)\b',question,re.I):return False
    return bool(re.match(r'\s*(?:please\s+)?(?:explain|describe|summari[sz]e|quote)\s+(?:(?:the|this|these|its|a)\s+)?(?:marker(?:\s+comments?)?|comments?)\b',question,re.I)
        or re.match(r'\s*what\s+(?:does|do)\s+(?:(?:the|this|these)\s+)?(?:marker|comment)s?\b.{0,80}\bmean\b',question,re.I))


def as_only_request(question):
    """Focus a literal AS question; compound and operational questions keep context."""
    roles=re.search(r'\blocal\b.{0,35}\b(?:remote|peer)\s+AS\b|\b(?:local|remote)[ -]?AS\b',question,re.I)
    other=re.search(r'\b(?:OSPF|router[ -]?ID|interface|static route|marker|comment|whole|entire|selected|highlighted|selection|session|state|health|troubleshoot|investigat\w*)\b',question,re.I)
    return bool(roles and not other)


def as_command_context(question,documents,path):
    """Project actual command lines, never a second renderer or AS inference.

    Multi-process buffers retain full context because peer/process attribution
    would need a richer parser than this bounded literal reader provides.
    """
    if not as_only_request(question):return []
    sections=[s for s in router_sections(documents,path) if s['protocol']=='BGP']
    if len(sections)!=1:return []
    section=sections[0]
    commands=[{'line':section['start'],'text':section['heading']}]
    commands.extend({'line':number,'text':line.strip()}
        for document in documents if document.get('source')==path
        for number,line in enumerate(document.get('text','').splitlines(),document.get('start_line',1))
        if section['start']<number<=section['end'] and re.fullmatch(r'neighbor\s+\S+\s+remote-as\s+\S+',line.strip(),re.I))
    return commands if len(commands)>1 else []


def verify_editor_router_ids(answer, documents, path, *, question='', source_kind='editor'):
    """Do not attribute a literal OSPF router-id to BGP (or vice versa).

    Selected literal AS/interface/route checks augment the original router-ID
    guard; the function name remains compatible. Other explanations remain
    interpretations, not certified CLI semantics.
    On failure reconstruct a source outline instead of releasing the claim.
    """
    uploaded = source_kind == 'uploaded'
    source_description = ('This describes uploaded configuration text; current device state is unverified. An upload to a device is not established. **No editor changes or device actions were performed.**'
                          if uploaded else 'This describes the supplied editor buffer; current device state is not established. **No changes were proposed or saved.**')
    comments=[line.strip() for document in documents if document.get('source')==path
              for line in document.get('text','').splitlines() if line.lstrip().startswith(('!','#','//'))][:12]
    comment_violation=False
    if comments:
        comment_prose=answer
        for comment in comments:comment_prose=comment_prose.replace(comment,'COMMENT_ANNOTATION')
        # A quoted CLI comment starts with "! "; it is not the end of a prose
        # sentence. Check attribution without splitting inside that literal.
        for sentence in re.split(r'(?<=[.!?])\s+|\n',comment_prose):
            if re.search(r'\b(?:does not|do not|cannot|can.t|not necessarily|doesn.t|don.t)\b',sentence,re.I):continue
            if re.search(r'\b(?:comments?|markers?|labels?)\b.{0,100}\b(?:indicates?|suggests?|means?|proves?|confirms?|implies)\b.{0,200}\b(?:frozen|held in a (?:specific |particular )?state|not saved|saved to|running on|applied to|configuration database|persistent storage)\b',sentence,re.I):
                comment_violation=True
        marker_only=comment_only_request(question)
        if comment_violation and marker_only:
            return (('The uploaded file' if uploaded else 'The open buffer')+' contains these author-written comments:\n\n'+'\n'.join('- `'+line.replace('`','\\`')+'`' for line in comments)+
                '\n\nA comment labels or annotates the text; it does not execute a protocol command. The label alone **does not establish** protocol state, whether the configuration is saved, or why the author chose it. Check editor status or an actual device/configuration record for those facts.\n\n**Source:** `'+path+'`. No changes were proposed or saved.'),True
    sections=router_sections(documents,path)
    from .editor_facts import literal_facts, contradicted_claims
    facts=literal_facts(documents,path)
    violations=contradicted_claims(answer,facts)
    if not sections and not violations and not comment_violation:return answer,False
    ids={protocol:{match[1] for section in sections if section['protocol']==protocol
         for command in section['commands']
         if (match:=re.fullmatch(r'(?:bgp\s+)?router-id\s+(\S+)',command,re.I))}
         for protocol in {section['protocol'] for section in sections}}
    scope=None;invalid=bool(violations) or comment_violation
    # Author comments/filenames cannot change the actual editor access state.
    access={document['read_only'] for document in documents if document.get('source')==path and isinstance(document.get('read_only'),bool)}
    if access=={False} and re.search(r'\b(?:buffer|document|file|draft|configuration)\b.{0,120}\b(?:not editable|not modifiable|read[- ]only|cannot be (?:edited|modified))\b',answer,re.I):
        invalid=True
    if re.search(r'\bAS\s+(?:roles?|values?|numbers?)\b|\blocal\s+and\s+remote\s+AS\b',question,re.I):
        required=set(facts['local_as'])|{value for values in facts['neighbors'].values() for value in values}
        explanatory_prose=re.sub(r'```.*?```','',answer,flags=re.S)
        mentioned=set(re.findall(r'(?:\bAS\s*|(?<!\w))(\d+)\b',explanatory_prose,re.I))
        if required and not required<=mentioned:invalid=True
    if facts['local_as'] and re.search(r'\b(?:AS\)?\s+roles?|autonomous system\s+(?:role|identifier))\s*[*:=-]*\s*OSPF\b',answer,re.I):invalid=True
    if uploaded and re.search(r'\b(?:was|were|has been)\s+(?:uploaded|saved|applied)\s+(?:to|on)\s+(?:the|a)\s+(?:router|device)\b',answer,re.I):
        invalid=True
    if as_only_request(question):
        if path and re.search(r'\b(?:filename|file name)\b.{0,50}\b(?:not provided|not supplied|unavailable|unknown)\b',answer,re.I):invalid=True
        if len(facts['local_as'])==1 and len(facts['neighbors'])==1:
            remote=next(iter(facts['neighbors'].values()))
            if len(remote)==1 and remote!=facts['local_as']:
                for clause in re.split(r'(?<=[.!?])\s+|\n',answer):
                    if re.search(r'\b(?:not|cannot|could|may|might|if)\b',clause,re.I):continue
                    if re.search(r'\b(?:ensur\w*|indicat\w*|means?|therefore)\b.{0,90}\b(?:same|one)\s+(?:network|autonomous system|AS)\b',clause,re.I):invalid=True
    if 'BGP' in ids:
        if not ids['BGP'] and re.search(r'\bBGP\s+router[ -]?id\b.{0,100}\b(?:infer\w*|assum\w*|deriv\w*)\b.{0,30}\b\d',answer,re.I):invalid=True
        for value in re.findall(r'\bBGP\s+(?:router[ -]?)?ID\s*(?:(?:is|of|as|equals)\s+|[:=]\s*)?([\d.]+)',answer,re.I):
            if value.rstrip('.') not in ids['BGP']:invalid=True
    for protocol,configured in ids.items():
        if configured:continue
        for clause in re.split(r'(?<=[.!?;])\s+|\n|\b(?:while|whereas|but)\b',answer,flags=re.I):
            claim=re.search(r'\b'+protocol+r'\b.{0,55}\b(?:specifies|configures|sets|includes|defines)\b.{0,45}\brouter[ -]?id\b',clause,re.I)
            claim=claim or re.search(r'\b'+protocol+r'\s+router[ -]?id\b.{0,20}\b(?:is|was)\s+(?:explicitly\s+)?(?:configured|set|specified|present)\b',clause,re.I)
            negated_prefix=claim and re.search(r'\b(?:no(?:\s+explicit)?|without(?:\s+an?)?)\s*$',clause[:claim.start()],re.I)
            if claim and not negated_prefix and not re.search(r'\b(?:no|not|without|doesn.t)\b',claim[0],re.I):invalid=True
    for line in answer.splitlines():
        plain=re.sub(r'[*`#]','',line).strip()
        heading=re.match(r'^(?:[-\d.)]+\s*)?(BGP|OSPF)\b',plain,re.I)
        if heading:scope=heading[1].upper()
        if not re.search(r'\brouter[ -]?id\b',plain,re.I):continue
        explicit=re.search(r'\b(BGP|OSPF)\b[^.!?\n]{0,40}\brouter[ -]?id\b',plain,re.I)
        attributed=explicit[1].upper() if explicit else scope
        values=re.findall(r'\brouter[ -]?id\b\s*(?:is|of|to|as|equals|:|=)?\s*([\d.]+)',plain,re.I)
        if attributed in ids and any(value.rstrip('.') not in ids[attributed] for value in values):invalid=True
    # Validate explicit wildcard-to-prefix paraphrases against their source
    # commands. This does not validate routing behavior or infer runtime state.
    import ipaddress
    prefixes={}
    for section in sections:
        for command in section['commands']:
            match=re.fullmatch(r'network\s+([\d.]+)\s+([\d.]+)\s+area\s+\S+',command,re.I)
            if not match:continue
            try:
                mask=str(ipaddress.IPv4Address(0xffffffff ^ int(ipaddress.IPv4Address(match[2]))))
                prefix=str(ipaddress.IPv4Network(match[1]+'/'+mask,strict=False))
                prefixes.setdefault(match[1],set()).add(prefix)
            except ValueError:continue  # Noncontiguous wildcard: preserve literal CLI.
    for value in re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b',answer):
        if value.split('/')[0] in prefixes and value not in prefixes[value.split('/')[0]]:invalid=True
    if re.search(r'\b(?:not currently active|not (?:currently )?running on (?:the |a )?device|currently (?:active|running) on (?:the |a )?device)\b',answer,re.I):invalid=True
    if not invalid:return answer,False
    if as_only_request(question) and len(facts['local_as'])==1 and facts['neighbors']:
        parts=[('The uploaded configuration' if uploaded else 'The draft')+' distinguishes **this router’s AS** from **its peer’s AS**:']
        parts.extend('- **Local AS:** `'+value+'`, from the BGP process heading.' for value in sorted(facts['local_as']))
        for peer,remote in facts['neighbors'].items():
            parts.append('- **Neighbor `'+peer+'`:** expected **remote AS** `'+', '.join(sorted(remote))+'`, from its `remote-as` command.')
        parts.append('The local AS identifies this router’s autonomous system; `remote-as` declares the autonomous system expected from that peer. These values configure the relationship; they do not establish that a BGP session is up.\n\n**Source:** `'+path+'`. No changes were proposed or saved.')
        return '\n\n'.join(parts),True
    parts=[('The uploaded configuration contains the routing sections below. The explanation is limited to commands explicitly present in this file.' if uploaded else
            'The supplied **editor buffer** contains the routing sections below. The explanation is limited to commands explicitly present in this buffer.')]
    if re.search(r'\b(?:compare|contrast|comparison)\b',question,re.I) and {'OSPF','BGP'}.issubset(ids):
        summary=[]
        for protocol in ['OSPF','BGP']:
            present=[command for section in sections if section['protocol']==protocol for command in section['commands']]
            fields=[]
            if ids[protocol]:fields.append('an explicit router ID')
            if protocol=='OSPF' and any(re.fullmatch(r'network\s+\S+\s+\S+\s+area\s+\S+',command,re.I) for command in present):fields.append('a network/area statement')
            if protocol=='BGP':
                fields.append('the local AS in its heading')
                if any(re.fullmatch(r'neighbor\s+\S+\s+remote-as\s+\S+',command,re.I) for command in present):fields.append('a neighbor/remote-AS statement')
            summary.append('**'+protocol+'** contains '+', '.join(fields or ['the shown protocol heading'])+('.' if ids[protocol] else ', with no explicit router-ID command.'))
        parts=[' '.join(summary)+' These are configured text differences; this buffer does not establish adjacency or session health.']
    for section in sections:
        protocol=section['protocol']
        parts.append('### '+protocol+'\n\n`'+section['heading']+'` · lines '+str(section['start'])+'–'+str(section['end']))
        configured=[command for command in section['commands'] if re.fullmatch(r'(?:bgp\s+)?router-id\s+\S+',command,re.I)]
        if configured:parts.append('- **Explicit router ID:** `'+configured[0].split()[-1]+'`.')
        if protocol=='BGP':
            parts.append('- **Local AS:** `'+section['heading'].split()[-1]+'`.')
            for command in section['commands']:
                peer=re.fullmatch(r'neighbor\s+(\S+)\s+remote-as\s+(\S+)',command,re.I)
                if peer:parts.append('- **Neighbor:** `'+peer[1]+'` · **remote AS:** `'+peer[2]+'`.')
        if not configured:parts.append('No explicit router ID appears in this shown '+protocol+' section; its effective router ID is not established by this text.')
        commands=section['commands'][:20]
        if commands:parts.append('```ios\n'+'\n'.join(commands)+'\n```')
    markers=[line.strip() for document in documents if document.get('source')==path
             for line in document.get('text','').splitlines() if line.startswith(('hostname ','!'))]
    if markers:parts.append('Other source lines: '+'; '.join('`'+line[:160]+'`' for line in markers[:5])+'.')
    additional=[(number,line) for number,line in facts['lines'] if re.match(r'\s*(?:interface |ip address |ip route )',line)]
    if additional:
        parts.append('**Additional source commands**\n\n```ios\n'+'\n'.join(line for _,line in additional[:40])+'\n```')
    parts.append('**Source:** `'+path+'`. '+source_description)
    return '\n\n'.join(parts),True

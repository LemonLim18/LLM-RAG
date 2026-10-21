"""Conversation coordination inside the existing V9 subprocess authority.

V9 selects operations, extracts parameters and finalizes tasks. No application
catalog, schema, renderer or independent parameter memory is introduced here.
"""
import re


def apply_reply(pipeline,plan,reply,task_id,inventory):
    from app.planner.models import PlannedTask
    tasks=[t for t in plan.tasks if t.intent_id==task_id] if task_id else plan.tasks
    if len(tasks)!=1:
        # Only an explicit ordinal can disambiguate a multi-task correction.
        match=re.search(r'\b(?:task|operation)\s+(\d+)\b',reply,re.I)
        tasks=[plan.tasks[int(match[1])-1]] if match and 1<=int(match[1])<=len(plan.tasks) else []
    if len(tasks)!=1:raise ValueError('Choose the operation task to correct in the review; the other tasks were preserved.')
    old=tasks[0]
    hosts=[d['hostname'] for d in inventory if any(re.search(r'(?<![\w-])'+re.escape(ref)+r'(?![\w-])',reply,re.I) for ref in [d['hostname'],*d.get('aliases',[])])]
    unknown=[v for v in re.findall(r'\b(?:R|SW|RTR|EDGE)[-_]?\d+\b',reply,re.I) if not any(v.casefold()==d['hostname'].casefold() for d in inventory)]
    hosts=list(dict.fromkeys(hosts+unknown)) or [d['hostname'] for d in old.target_devices] or old.target_refs
    operation=pipeline._explicit_operation(reply,pipeline.load_operations()) or old.operation_id
    if not operation or re.search(r'\b(set|configure|enable|disable|add|remove)\b',reply,re.I):
        # Existing V9 operation selector, bounded to its active published catalog.
        # This also works when the optional published vector index is offline.
        category=pipeline.classify_category(old.request_text+'\nLatest correction: '+reply)
        candidates=[item for item in pipeline.load_operations() if pipeline.get_operation(item['operation_id'])['category_id']==category]
        operation=pipeline.select_operation(reply,category,candidates)
    metadata=pipeline.get_operation(operation);schema=pipeline.load_schema(operation)
    old_extraction=pipeline.extract_parameter_result(old.request_text,schema)
    # Adapt conversational assignment wording to V9's field-scoped literal
    # grammar. Values remain the original user text; V9 extracts and validates.
    from app.parameters.evidence import field_terms
    normalized=reply
    for key,node in schema.get('properties',{}).items():
        terms='|'.join(re.escape(term) for term in field_terms(key,node))
        def assignment(match):
            value=match[2].strip()
            # Sentence punctuation is not part of an unquoted assignment.
            # Quoted values (including intentional punctuation) are untouched.
            if not value.startswith(('\"', "'")):value=value.removesuffix('.')
            return match[1]+': '+value
        normalized=re.sub(r'(?<![\w])('+terms+r')\s+to\s+([^\n]+)$',assignment,normalized,flags=re.I)
    extraction=pipeline.extract_parameter_result(normalized,schema)
    parameters={k:v for k,v in old_extraction.parameters.items() if k in schema.get('properties',{}) and v is not None}
    parameters.update({k:v for k,v in old.parameters.items() if k in schema.get('properties',{}) and not old.parameter_provenance.get(k,'').startswith('context:')})
    parameters.update({k:v for k,v in extraction.parameters.items() if v is not None and v!=''})
    updated=pipeline._finalize_task(intent_id=old.intent_id,request_text=old.request_text+'\nLatest engineer correction: '+reply,
        category=metadata['category_id'],operation_id=operation,parameters=parameters,
        parameter_provenance={k:'clarification_user' for k in parameters},target_refs=hosts,
        clarification_history=old.clarification_history)
    plan.tasks[plan.tasks.index(old)]=updated
    return plan

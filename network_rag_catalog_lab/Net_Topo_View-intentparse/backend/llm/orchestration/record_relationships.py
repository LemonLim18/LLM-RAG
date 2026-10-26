"""Checks over offered identities and relationships, not a network parser."""
import re


def record_relationship_errors(answer,context,question):
    text=re.sub(r'[*`]','',answer);errors=[]
    devices=[d for item in context if item['tool']=='inventory.read' and item['status']=='success'
             for d in (item.get('data') or {}).get('devices',[])]
    if devices and all(item['tool']=='inventory.read' for item in context):
        for clause in re.split(r'(?<=[.!?])\s+|\n',text):
            if re.search(r'\b(?:not established|not prove|not imply|cannot establish|may|could|unknown)\b',clause,re.I):continue
            if re.search(r'\b(?:part of|present in|installed in)\s+(?:the\s+)?routing table\b',clause,re.I) and not re.search(r'\bnot\s+(?:necessarily\s+)?(?:part of|present in|installed in)\s+(?:the\s+)?routing table\b',clause,re.I):
                errors.append('Address inventory does not establish route-table installation; a routing observation is required for that claim')
            if re.search(r'\b(?:management|mgmt)\b[^.!?\n]{0,180}\b(?:not routable|non.?routable|rather than (?:a |an )?routable)\b',clause,re.I):
                errors.append('A management-address role does not establish that its IP is non-routable; distinguish endpoint purpose from observed reachability')
    addresses=(re.search(r'\b(?:management|mgmt)\b',question,re.I)
        and re.search(r'\b(?:routed|interfaces?)\b',question,re.I)
        and re.search(r'\b(?:addresses?|IPs?)\b',question,re.I))
    for device in devices:
        ports=device.get('interfaces',[])
        if addresses and any(value and str(value) not in text for value in
                [device.get('management_ip'),*[p.get('ip_address') for p in ports]]):
            errors.append('The requested management/routed-address comparison omits actual returned addresses; role labels or a citation do not fulfill the value request')
        management=[p for p in ports if p.get('interface_type') in {'management','mgmt'}
                    or p.get('ip_address') and p.get('ip_address')==device.get('management_ip')]
        if not management:
            for clause in re.split(r'(?<=[.!?])\s+|\n',text):
                if device['hostname'].casefold() not in clause.casefold() and len(devices)!=1:continue
                if re.search(r'\b(?:no|not|unknown|unrecorded|would|could|may|typically|generally)\b',clause,re.I):continue
                if re.search(r'\bmanagement\s+(?:interface|port)\b',clause,re.I):
                    errors.append('A management endpoint address does not establish a recorded management-interface entity; preserve entity ownership')
    links=[]
    for item in context:
        if item['tool']!='network.topology' or item['status']!='success':continue
        data=item.get('data') or {};links.extend(data.get('links',[]))
        links.extend(r['link_endpoints'] for r in data.get('records',[]) if r.get('link_endpoints'))
    pairs=[((str(r['source']),str(r['source_interface'])),(str(r['target']),str(r['target_interface'])))
           for r in links if all(r.get(k) for k in ['source','source_interface','target','target_interface'])]
    if pairs and all(item['tool']=='network.topology' for item in context):
        names=sorted({v[0] for pair in pairs for v in pair},key=len,reverse=True)
        ports=sorted({v[1] for pair in pairs for v in pair},key=len,reverse=True)
        pattern='('+'|'.join(re.escape(v) for v in names)+r')\s*(?:[/,:]\s*|\s+(?:(?:interface|port)\s+)?)('+'|'.join(re.escape(v) for v in ports)+r')(?![\w/]|\.\w)'
        allowed={tuple((n.casefold(),p.casefold()) for n,p in pair) for pair in pairs}
        allowed|={tuple(reversed(pair)) for pair in list(allowed)}
        for clause in re.split(r'\n|(?<=[!?])\s+|;\s*',text):
            endpoints=re.findall(pattern,clause,re.I)
            for left,right in zip(endpoints,endpoints[1:]):
                if left[0].casefold()==right[0].casefold():continue
                if tuple((n.casefold(),p.casefold()) for n,p in [left,right]) not in allowed:
                    errors.append('The claimed endpoint pair is not a returned topology relationship; membership alone does not establish that connection')
    for tool,label in [('knowledge.search',r'published\s+(?:[\w-]+\s+){0,2}(?:requirements?|contracts?|methods?)'),
                       ('network.configuration',r'saved\s+(?:settings|configuration|captures?)')]:
        if not any(item['tool']==tool and item['status']=='success' and item.get('data') for item in context):continue
        for clause in re.split(r'(?<=[.!?])\s+|\n',text):
            if re.search(r'\b(?:complete|full|specific|requested|parameter|field)\b',clause,re.I):continue
            if re.search(label+r'[^.!?\n]{0,100}\b(?:not provided|not retrieved|not available|no information)\b',clause,re.I):
                errors.append('The answer denies a supplied source family; distinguish an absent field or incomplete contract from absent retrieved evidence')
    return list(dict.fromkeys(errors))

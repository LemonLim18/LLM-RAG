import json,re
from .catalog import load_categories
from .llm import llm

def classify_category(prompt):
    cats=load_categories(); valid={x['category_id'] for x in cats}
    listing='\n'.join(f"- {x['category_id']}: {x['description']}" for x in cats)
    msg=f'''You classify network requests. Choose exactly one category from:\n{listing}\nReturn JSON only: {{"category":"<category_id>"}}'''
    raw=llm.invoke([('system',msg),('human',prompt)]).content.strip()
    try: category=json.loads(raw)['category'].lower()
    except Exception:
        m=re.search(r'"category"\s*:\s*"([^"]+)"',raw,re.I); category=m.group(1).lower() if m else ''
    if category in valid:return category
    # deterministic fallback for a small local prototype
    for c,keys in {'ospf':['ospf'],'bgp':['bgp','peer','peering','neighbor'],'isis':['isis','is-is'],'vlan':['vlan','trunk'],'static_routing':['static route','ip route'],'ip_address':['ip address','ipv4 address']}.items():
        if any(k in prompt.lower() for k in keys): return c
    raise ValueError(f'Cannot classify category. LLM returned: {raw}')

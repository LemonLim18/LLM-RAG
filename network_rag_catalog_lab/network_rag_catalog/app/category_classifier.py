import json,re
# . means importing from the local package (app)
from .catalog import load_categories
from .llm import llm

def classify_category(prompt):
    cats=load_categories(); # Get the list of categories from the catalog directory 
    # Create a set of valid category IDs from the list
    valid={x['category_id'] for x in cats}  
    # Create a formatted list of categories for the prompt
    listing='\n'.join(f"- {x['category_id']}: {x['description']}" for x in cats)
    # Create a message for the LLM to classify the prompt into one of the categories
    msg=f'''You classify network requests. Choose exactly one category from:\n{listing}\nReturn JSON only: {{"category":"<category_id>"}}'''
    # Invoke the LLM with the system message and the user prompt, and get the raw output
    raw=llm.invoke([('system',msg),('human',prompt)]).content.strip()
    # Once it returns the raw (category: category_id), it will extract the category_id in lowercase
    try: 
        category=json.loads(raw)['category'].lower()
    # Else, trynna find the category_id in the raw string using regex. If found, return it in lowercase. If not found, return an empty string.
    except Exception:
        m=re.search(r'"category"\s*:\s*"([^"]+)"',raw,re.I); category=m.group(1).lower() if m else ''

    # If the extracted category is in the valid set, return it. 
    if category in valid:
        return category


    # NOT-SO-INTELLIGENT DETERMINISTIC FALLBACK
    # Else, use a deterministic fallback to classify the prompt based on keywords. 
    for c,keys in {'ospf':['ospf'],'bgp':['bgp','peer','peering','neighbor'],'isis':['isis','is-is'],'vlan':['vlan','trunk'],'static_routing':['static route','ip route'],'ip_address':['ip address','ipv4 address']}.items():
        if any(k in prompt.lower() for k in keys): return c
    # If no category can be classified, raise a ValueError with the raw output from the LLM.
    raise ValueError(f'Cannot classify category. LLM returned: {raw}')

from jinja2 import Environment,FileSystemLoader,StrictUndefined
from .template_selector import select_template

def render(device,operation_id,params):
    p=select_template(device,operation_id); env=Environment(loader=FileSystemLoader(str(p.parent)),undefined=StrictUndefined,trim_blocks=True,lstrip_blocks=True)
    context=dict(params)
    if 'prefix_length' in context:
        context['netmask']=str(__import__('ipaddress').IPv4Network(f"0.0.0.0/{context['prefix_length']}").netmask)
    return env.get_template('template.j2').render(**context).strip()+'\n'

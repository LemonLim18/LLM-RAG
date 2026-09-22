from jinja2 import Environment,FileSystemLoader,StrictUndefined
from .template_selector import select_template

def render(device,operation_id,params):
    # returns the path to the jinja template file for a given device and operation
    p=select_template(device,operation_id); 
    # Create a Jinja2 environment with the template file's parent directory as the loader, and set undefined variables to raise an error. Render the template with the provided parameters, and if 'prefix_length' is present, calculate the corresponding netmask and add it to the context. Return the rendered configuration as a string with a newline at the end.
    # Jinja template is like a fill-in-the-blank form
    # The environment creates the Jinja2 engine with the instructions about how the templates should be loaded and rendered.
    # undefined=StrictUndefined will raise an error when an undefined variable is encountered or the variable is not provided
    env=Environment(loader=FileSystemLoader(str(p.parent)),undefined=StrictUndefined,trim_blocks=True,lstrip_blocks=True)
    # The context is a dictionary that contains the parameters to be filled in the template.
    context=dict(params)
    # If 'prefix_length' is in the context, calculate the corresponding netmask and add it to the context.
    if 'prefix_length' in context:
        # __import__('ipaddress') is a way to import Python's ipaddress module dynamically.
        # It allows to convert the netmask from the prefix length (e.g., /24) to the standard dotted-decimal format (e.g., 255.255.255.0)
        context['netmask']=str(__import__('ipaddress').IPv4Network(f"0.0.0.0/{context['prefix_length']}").netmask)
    # This line means the the environment will load the Jinja2 config template called 'template.j2' at a predefined p path location, and then render it with the context dictionary. 
    # The rendered configuration is returned as a string with a newline at the end.
    return env.get_template('template.j2').render(**context).strip()+'\n'

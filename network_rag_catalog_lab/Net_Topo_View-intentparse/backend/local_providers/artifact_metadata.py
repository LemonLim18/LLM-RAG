"""Output declaration carried inside the reviewed, immutable Jinja asset."""
import json
import re


def artifact_metadata(template):
    # A Jinja comment survives publication without changing V9's binding model
    # or appearing in rendered configuration. Older templates retain their format.
    marker = re.match(r'\s*\{#\s*artifact\s*:(.*?)#\}', template, re.S)
    if not marker:
        return {'format': 'native_cli', 'language': 'text', 'extension': '.txt'}
    value = json.loads(marker.group(1))
    if not isinstance(value, dict) or set(value) != {'format', 'language', 'extension'}:
        raise ValueError('Artifact declaration requires format, language and extension.')
    for key in ('format', 'language'):
        if not isinstance(value[key], str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}', value[key]):
            raise ValueError('Invalid artifact ' + key)
    if not isinstance(value['extension'], str) or not re.fullmatch(r'\.[a-z0-9]{1,10}', value['extension']):
        raise ValueError('Artifact extension must be a simple file suffix.')
    return value

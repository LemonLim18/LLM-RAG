"""Recorded engineering facts augment existing inventory, never discovered telemetry."""
import json
from typing import Literal
from pydantic import Field, model_validator
from llm.gateway_models import StrictModel, text_digest


class EngineeringFacts(StrictModel):
    origin: Literal['planned','sample']
    model_family: str = Field(min_length=1,max_length=100)
    source_refs: dict[str,str] = Field(min_length=1,max_length=30)
    capabilities: dict = Field(default_factory=dict)
    vlans: list[dict] = Field(default_factory=list,max_length=4094)
    interfaces: list[dict] = Field(default_factory=list,max_length=500)
    resources: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def bounded_facts(self):
        if len(self.model_dump_json().encode('utf-8'))>100000:
            raise ValueError('Engineering facts exceed 100 KiB')
        if any(not key or not value.strip() or len(value)>2000 for key,value in self.source_refs.items()):
            raise ValueError('Engineering facts need bounded nonempty source references')
        ids=[v.get('vlan_id') for v in self.vlans]
        if any(type(value) is not int or not 1<=value<=4094 for value in ids) or len(set(ids))!=len(ids):
            raise ValueError('VLAN identities must be unique integers 1–4094')
        names=[v.get('name') for v in self.interfaces]
        if any(not isinstance(name,str) or not name for name in names) or len(set(names))!=len(names):
            raise ValueError('Interface fact names must be unique and nonempty')
        return self


def facts_revision(value):
    return text_digest(json.dumps(value,sort_keys=True,separators=(',',':')))


def project_facts(device, facts):
    """Identity/software/interfaces come from SQLite; facts cannot override them."""
    if not facts: return device
    validated=EngineeringFacts.model_validate(facts)
    overrides={row['name']:row for row in validated.interfaces}
    projected={**device, **{key:getattr(validated,key) for key in ['model_family','source_refs','capabilities','vlans','resources']},
        'engineering_facts_origin':validated.origin}
    projected['interfaces']=[{**row,**overrides.get(row['name'],{}),'name':row['name']} for row in device['interfaces']]
    return projected

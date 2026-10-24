"""Logical development sources mapped to existing authorized capabilities.

Registry metadata grants no authority. File/document/session entries describe
their existing ingestion path and are not fabricated network-reader records.
"""
from dataclasses import asdict,dataclass


@dataclass(frozen=True)
class Source:
    key:str
    title:str
    tool:str
    domain:str|None
    kind:str
    editor:str='records'
    description:str=''
    aliases:tuple[str,...]=()
    additional_readers:tuple[str,...]=()
    reader_record_kinds:tuple[tuple[str,tuple[str,...]],...]=()

    def supports(self, tool):
        """Compatibility metadata only; each reader still authorizes execution."""
        return tool==self.tool or tool in self.additional_readers

    @property
    def readers(self):
        return (self.tool,*self.additional_readers)

    def record_kinds(self, tool):
        return dict(self.reader_record_kinds).get(tool,(self.kind,)) if self.supports(tool) else ()


SOURCES=(
    Source('inventory','Planned inventory','inventory.read',None,'inventory','inventory'),
    Source('topology_planned','Planned links','network.topology',None,'planned_links','links',aliases=('planned topology','intended topology')),
    Source('topology_observed','Observed links','network.topology','topology','observed_link',aliases=('observed topology','discovered topology')),
    Source('topology_history','Topology history','network.topology','topology','observed_link',aliases=('historical topology',)),
    Source('device_state','Device and interface state','network.state','state','interface_state'),
    Source('running_configs','Current configuration','network.configuration','running_configuration','running_configuration','configuration'),
    Source('config_snapshots','Saved configurations','network.configuration','configuration','configuration_snapshot','configuration'),
    Source('config_changes','Configuration changes','network.configuration','configuration','configuration_change'),
    Source('routing_state','Routing and forwarding','network.state','state','routing_table'),
    Source('protocol_state','OSPF and BGP','network.state','state','protocol_observation'),
    Source('controller_state','Controller state','network.state','state','controller_state',description='Controller name, configured connection, capabilities and associated device. Describes the controller connection, not router health.'),
    Source('telemetry','Telemetry samples','network.telemetry','telemetry','metric_sample'),
    Source('interface_metrics','Interface counters','network.telemetry','telemetry','interface_counters',description='Authored per-interface traffic/error counter records and their samples. Preserve units and sample windows. The separately declared observation model exposes calculated metric_series through the simulation source on the same telemetry reader.'),
    Source('syslog','Syslog','network.syslog','syslog','syslog_event'),
    Source('incidents','Incidents and alerts','network.incidents','incidents','incident'),
    Source('config_drift','Configuration drift','network.configuration','configuration','configuration_drift'),
    Source('source_health','Source health','network.state','state','source_health',description='Collector availability, per-source status and physical_collection_performed: whether collection from physical devices actually ran.'),
    Source('jobs_audit','Simulated jobs and audit','network.state','state','simulated_job',description='Simulated validation job outcomes and recorded effects, distinct from actual deployment and audit history.'),
    Source('knowledge','Published V9 references','knowledge.search',None,'knowledge','knowledge',aliases=('scenario knowledge reference','knowledge references')),
    Source('documents','Technical documents','document.read',None,'document','files'),
    Source('attachments','Conversation attachments','document.read',None,'attachment','files'),
    Source('diagrams','Images and diagrams','document.read',None,'diagram','files'),
    Source('conversation','Conversation setup','conversation.turn',None,'conversation','conversation'),
    Source('simulation','Bounded simulation','network.state','state','simulation','simulation',
        description='Declared observation model: forwarding paths, routing and protocol assessments through network.state; modeled measurement series, counter rates and utilization through network.telemetry. Calculations retain their declared inputs, units, sampling window and limitations.',
        additional_readers=('network.telemetry',),
        reader_record_kinds=(('network.state',('forwarding_assessment','protocol_assessment','routing_table','interface_state')),
            ('network.telemetry',('metric_series',)))),
)
BY_KEY={source.key:source for source in SOURCES}
STATUSES=('AVAILABLE','MISSING','UNAVAILABLE','STALE','ERROR','CONFLICTING','UNSUPPORTED','NOT_QUERIED')


def catalog():return [asdict(source) for source in SOURCES]


def reader_domains(keys, preferred=()):
    """Keep a compatible chosen reader; use the primary only when unresolved.

    This maps source identity to reader shape. It neither selects entities nor
    grants capabilities, and an unrelated preferred reader is never admitted.
    """
    domains=[]
    for key in keys:
        source=BY_KEY[key]
        selected=[domain for domain in preferred if source.supports(
            {'inventory':'inventory.read','knowledge':'knowledge.search'}.get(domain,'network.'+domain))]
        domains.extend(selected or ['knowledge' if source.tool=='knowledge.search' else
            'inventory' if source.tool=='inventory.read' else source.tool.removeprefix('network.')])
    return list(dict.fromkeys(domains))


def explicit_read_sources(prompt,available):
    """Resolve explicitly named registry sources inside read/source-use clauses.

    This supplies a retrieval constraint, not a semantic operation classifier or
    authorization. Attachment/editor questions keep their distinct context path.
    """
    import re
    from llm.gateway_references import read_intent_text
    prompt=read_intent_text(prompt)
    if re.search(r'\b(?:attached|uploaded|editor|buffer|open file|this (?:pdf|document|file))\b',prompt,re.I):return []
    clauses=re.findall(r'\b(?:use|consult|from|read|show|fetch|obtain|compare|inspect|check|list)\s+([^.;\n]+)',prompt,re.I)
    output=[]
    for clause in clauses:
        # Registry names are source identities, not spelling-sensitive commands.
        # Normalize separators in this name-matching view only, never in entity
        # names, original prompts, source records or model-visible evidence.
        clause=re.sub(r'[_\-\u2010-\u2015]+',' ',clause)
        clause=re.split(r',?\s+\b(?:not|rather than|instead of|excluding)\b',clause,flags=re.I)[0]
        health_attributes=bool(re.search(r'\bsource health\b',clause,re.I))
        health_subject=re.search(r'\bsource health(?:\s+(?:records?|status|availability|claims?))*\s+(?:for|of|about)\b',clause,re.I)
        for key,source in BY_KEY.items():
            if key not in available or not (source.tool.startswith('network.') or key=='knowledge'):continue
            names={source.title,*source.aliases} if key=='knowledge' else {key.replace('_',' '),source.title,*source.aliases}
            if key!='knowledge' and sum(other.kind==source.kind for other in SOURCES)==1:names.add(source.kind.replace('_',' '))
            matches=[match for name in names for match in re.finditer(r'(?<![\w-])'+re.escape(name)+r's?(?![\w-])',clause,re.I)]
            if key==source.domain:
                # Naming the shared telemetry reader authorizes that reader's
                # domain, not only its CPU/memory logical source. Let the
                # existing source planner choose the requested measurement.
                matches=[match for match in matches if not re.match(r'\s+(?:reader|tool)\b',clause[match.end():],re.I)]
            # A named category's health claim/status is an attribute of the
            # health record, not a request for its measurements or documents.
            if health_attributes and key!='source_health':
                matches=[match for match in matches if not re.match(r'\s+(?:source\s+)?(?:claim|status|availability)\b',clause[match.end():],re.I)]
                if health_subject:
                    matches=[match for match in matches if match.start()<health_subject.end() or
                        re.match(r'\s+(?:samples?|measurements?|events?|counters?|messages?)\b',clause[match.end():],re.I)]
            if matches:output.append(key)
    return list(dict.fromkeys(output))

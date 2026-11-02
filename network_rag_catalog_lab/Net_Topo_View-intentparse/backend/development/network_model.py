"""Bounded IPv4 observation model, consumed by the existing scenario manager.

No packets or protocol processes run. Only explicitly modeled tables, neighbor
resolution, ordered stateless ACLs and interface state establish these outcomes.
"""
from collections import deque
from datetime import datetime
import ipaddress
from typing import Literal,get_args
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class NextHop(Model):
    interface_id: int | None = None
    address: str | None = None
    resolved: bool | None = None


class Route(Model):
    id: str
    prefix: str
    origin: Literal['connected', 'static', 'ospf', 'bgp']
    preference: int = Field(ge=0, le=255)
    metric: int = Field(default=0, ge=0)
    action: Literal['forward', 'discard', 'leak'] = 'forward'
    next_hops: list[NextHop] = Field(default_factory=list, max_length=16)
    leak_to_vrf: str | None = None


class Table(Model):
    device_id: int
    vrf: str = 'default'
    complete: bool = False
    routes: list[Route] = Field(default_factory=list, max_length=500)


class ACLRule(Model):
    id: str
    source: str = '0.0.0.0/0'
    destination: str = '0.0.0.0/0'
    protocol: Literal['ip', 'icmp', 'tcp', 'udp'] = 'ip'
    source_port: int | None = Field(default=None, ge=0, le=65535)
    destination_port: int | None = Field(default=None, ge=0, le=65535)
    action: Literal['permit', 'deny']


class Policy(Model):
    id: str
    interface_id: int
    direction: Literal['ingress', 'egress']
    vrf: str = 'default'
    rules: list[ACLRule] = Field(default_factory=list, max_length=200)
    default_action: Literal['permit', 'deny']


class Flow(Model):
    id: str
    source_device_id: int
    destination_device_id: int
    source_address: str
    destination_address: str
    vrf: str = 'default'
    destination_vrf: str = 'default'
    protocol: Literal['icmp', 'tcp', 'udp'] = 'icmp'
    source_port: int | None = Field(default=None, ge=0, le=65535)
    destination_port: int | None = Field(default=None, ge=0, le=65535)
    require_return: bool = True


class OSPFPeer(Model):
    device_id: int
    interface_id: int
    router_id: str
    area: str
    process: str | None = None  # local identity; equality across vendors is unnecessary
    area_type: Literal['normal','stub','nssa'] | None = None
    hello_seconds: int = Field(gt=0)
    dead_seconds: int = Field(gt=0)
    network_type: Literal['broadcast', 'point_to_point', 'non_broadcast']
    authentication: str | None = None  # opaque compatibility label; never a credential
    mtu: int | None = Field(default=None, ge=576, le=65535)
    mtu_ignore: bool | None = None
    passive: bool = False
    role: Literal['DR', 'BDR', 'DROther', 'point_to_point', 'unknown'] = 'unknown'


class OSPFSession(Model):
    id: str
    left: OSPFPeer
    right: OSPFPeer
    observed_state: Literal['Down', 'Init', '2-Way', 'ExStart', 'Exchange', 'Loading', 'Full', 'unknown']


class BGPPeer(Model):
    device_id: int
    address: str
    local_as: int = Field(ge=1, le=4294967295)
    remote_as: int = Field(ge=1, le=4294967295)
    vrf: str = 'default'
    update_source: str | None = None
    hold_seconds: int | None = Field(default=None,ge=0,le=65535)
    keepalive_seconds: int | None = Field(default=None,ge=0,le=21845)
    shutdown: bool = False
    authentication: str | None = None
    address_families: list[Literal['ipv4_unicast', 'ipv6_unicast']] = Field(default_factory=list, max_length=2)


class BGPSession(Model):
    id: str
    left: BGPPeer
    right: BGPPeer
    observed_state: Literal['Idle', 'Connect', 'Active', 'OpenSent', 'OpenConfirm', 'Established', 'unknown']
    transport_reachable: bool | None = None
    accepted_prefixes: list[str] | None = None
    rejected_prefixes: list[str] | None = None
    received_prefixes: list[str] | None = None
    advertised_prefixes: list[str] | None = None
    withdrawn_prefixes: list[str] | None = None
    rib_in_complete: bool | None = None
    rib_out_complete: bool | None = None
    next_hop_valid: bool | None = None
    policy_observed: bool = False


class Sample(Model):
    timestamp: str
    value: float | None = Field(default=None,ge=0,strict=True)


def validate_recorded_metric(values,captured_at):
    """Validate authored points using the same sample contract as the model.

    Custom metric names/units remain possible. Known units retain their exact
    bounds; missing points and counter resets remain observations, never zeroed.
    """
    import math
    value=values.get('value')
    if type(value) not in {int,float} or not math.isfinite(value) or value<0:
        raise ValueError('Metric value must be a finite nonnegative number')
    if not isinstance(values.get('unit'),str) or not values['unit'].strip():raise ValueError('Metric unit is required')
    if values['unit']=='percent' and value>100:raise ValueError('Percentage exceeds100')
    interval=values.get('sampling_seconds')
    if interval is not None and (type(interval) is not int or not 0<interval<=86400):raise ValueError('Sampling interval must be an integer from1 to86400 seconds')
    points=values.get('samples')
    if points is None:
        if values.get('metric') in get_args(MetricSeries.model_fields['metric'].annotation):
            # Validate the authored aggregate, without storing an invented series.
            MetricSeries(id='aggregate-validation',device_id=1,metric=values['metric'],
                unit={'bits_per_second':'bps'}.get(values['unit'],values['unit']),sampling_seconds=interval or 1,
                samples=[{'timestamp':captured_at,'value':value}])
        return
    if not isinstance(points,list) or not 1<=len(points)<=300:raise ValueError('Supply one to300 metric samples')
    captured=datetime.fromisoformat(captured_at.replace('Z','+00:00'))
    if not captured.tzinfo:raise ValueError('Metric capture time requires a timezone')
    times=[]
    for raw in points:
        point=Sample.model_validate(raw)
        at=datetime.fromisoformat(point.timestamp.replace('Z','+00:00'))
        if not at.tzinfo or at>captured:raise ValueError('Sample time must be timezone-aware and no later than its capture')
        if values['unit']=='percent' and point.value is not None and point.value>100:raise ValueError('Sample percentage exceeds100')
        times.append(at)
    if any(a>=b for a,b in zip(times,times[1:])):raise ValueError('Samples must have distinct increasing timestamps')
    if values.get('metric') in get_args(MetricSeries.model_fields['metric'].annotation):
        MetricSeries(id='recorded-validation',device_id=1,metric=values['metric'],unit={'bits_per_second':'bps'}.get(values['unit'],values['unit']),sampling_seconds=interval or 1,samples=points)


def metric_sample_window(values,start,end,interfaces,device_id,interface_id):
    """Clip actual samples; never reuse an aggregate from outside that window."""
    points=values.get('samples')
    if not isinstance(points,list):return None
    at=lambda raw:datetime.fromisoformat(raw.replace('Z','+00:00'))
    selected=[dict(point) for point in points if (not start or at(point['timestamp'])>=start) and (not end or at(point['timestamp'])<=end)]
    if not selected:return None
    outside={'delta','average_per_second','peak_utilization_pct','sampling_gaps','missing_values','counter_reset_or_wrap','interpretation'}
    result={key:value for key,value in values.items() if key in {'metric','unit','sampling_seconds','source_category','observation_basis'}}
    omitted=sorted(set(values)-set(result)-{'samples','value','window_start','window_end'}-outside)
    if omitted:result['unscoped_fields_omitted']=omitted
    result.update(samples=selected,value=selected[-1]['value'],window_start=selected[0]['timestamp'],window_end=selected[-1]['timestamp'],
        missing_values=any(point['value'] is None for point in selected),sample_window_filtered=True)
    if values.get('sampling_seconds') is not None and values.get('metric') in get_args(MetricSeries.model_fields['metric'].annotation):
        # The established bounded metric engine performs rate/reset/gap math.
        series=MetricSeries(id='scoped-window',device_id=device_id,interface_id=interface_id,
            metric=values['metric'],unit={'bits_per_second':'bps'}.get(values['unit'],values['unit']),sampling_seconds=values['sampling_seconds'],samples=selected)
        finding=metric_findings(NetworkModel(observed_at=selected[-1]['timestamp'],metrics=[series]),interfaces)[0]
        result.update(finding['values'],interpretation=finding['notes'])
        result['unit']=values['unit']  # Preserve the authored spelling of an exact unit alias.
    else:
        result['window_limitation']='No supported calculation contract and sampling interval for this series; continuity, rates and aggregates from outside this window were not inferred.'
    return result


class MetricSeries(Model):
    id: str
    device_id: int
    interface_id: int | None = None
    metric: Literal['in_bps','out_bps','errors','discards','queue_drops','loss_pct','latency_ms','jitter_ms','cpu_pct','memory_pct']
    unit: Literal['bps','count','percent','ms']
    sampling_seconds: int = Field(gt=0,le=86400)
    samples: list[Sample] = Field(min_length=1,max_length=300)

    @model_validator(mode='after')
    def coherent(self):
        expected='bps' if self.metric.endswith('_bps') else 'count' if self.metric in {'errors','discards','queue_drops'} else 'ms' if self.metric.endswith('_ms') else 'percent'
        if self.unit!=expected:raise ValueError('Metric unit does not match its declared measurement')
        times=[datetime.fromisoformat(p.timestamp.replace('Z','+00:00')) for p in self.samples]
        if any(not t.tzinfo for t in times) or any(a>=b for a,b in zip(times,times[1:])):raise ValueError('Metric samples require distinct increasing timezone-aware times')
        if self.unit=='percent' and any(p.value is not None and p.value>100 for p in self.samples):raise ValueError('Percentage outside 0..100')
        return self


class NetworkModel(Model):
    observed_at: str
    policy_attachments_complete: bool = False
    tables: list[Table] = Field(default_factory=list, max_length=300)
    policies: list[Policy] = Field(default_factory=list, max_length=300)
    flows: list[Flow] = Field(default_factory=list, max_length=30)
    ospf: list[OSPFSession] = Field(default_factory=list, max_length=100)
    bgp: list[BGPSession] = Field(default_factory=list, max_length=100)
    metrics: list[MetricSeries] = Field(default_factory=list,max_length=300)

    @model_validator(mode='after')
    def validate_values(self):
        if not datetime.fromisoformat(self.observed_at.replace('Z', '+00:00')).tzinfo:
            raise ValueError('Network observations need a timezone')
        ids = [r.id for t in self.tables for r in t.routes] + [p.id for p in self.policies] + [f.id for f in self.flows] + [s.id for s in self.ospf + self.bgp] + [m.id for m in self.metrics]
        if len(ids) != len(set(ids)): raise ValueError('Duplicate modeled source identity')
        if len({(t.device_id, t.vrf) for t in self.tables}) != len(self.tables): raise ValueError('Duplicate routing table')
        if len({(p.interface_id, p.direction, p.vrf) for p in self.policies}) != len(self.policies): raise ValueError('Ambiguous policy attachment')
        for table in self.tables:
            for route in table.routes:
                ipaddress.IPv4Network(route.prefix, strict=True)
                if route.action == 'forward' and not route.next_hops: raise ValueError('Forward route needs explicit next hops')
                if route.action == 'leak' and (not route.leak_to_vrf or route.leak_to_vrf == table.vrf): raise ValueError('Leak route needs a different declared table')
                for hop in route.next_hops:
                    if hop.address: ipaddress.IPv4Address(hop.address)
                    if hop.interface_id is None and hop.address is None: raise ValueError('Empty next hop')
        for policy in self.policies:
            if len({r.id for r in policy.rules}) != len(policy.rules): raise ValueError('Duplicate ACL rule identity')
            for rule in policy.rules:
                ipaddress.IPv4Network(rule.source); ipaddress.IPv4Network(rule.destination)
                if (rule.source_port is not None or rule.destination_port is not None) and rule.protocol not in {'tcp', 'udp'}:
                    raise ValueError('Ports require TCP/UDP')
        for flow in self.flows:
            ipaddress.IPv4Address(flow.source_address); ipaddress.IPv4Address(flow.destination_address)
        for session in self.ospf:
            ipaddress.IPv4Address(session.left.router_id); ipaddress.IPv4Address(session.right.router_id)
        for session in self.bgp:
            ipaddress.IPv4Address(session.left.address); ipaddress.IPv4Address(session.right.address)
            for peer in [session.left,session.right]:
                if peer.update_source:ipaddress.IPv4Address(peer.update_source)
            for field in ['accepted_prefixes','rejected_prefixes','received_prefixes','advertised_prefixes','withdrawn_prefixes']:
                for prefix in getattr(session,field) or []:ipaddress.IPv4Network(prefix, strict=True)
        return self

    def validate_references(self, devices, interfaces, logical_time):
        ds = {d.id for d in devices}; ifs = {i.id: i for i in interfaces}
        if datetime.fromisoformat(self.observed_at.replace('Z', '+00:00')) > logical_time: raise ValueError('Future network observation')
        def owned(device, interface):
            if device not in ds or interface not in ifs or ifs[interface].device_id != device: raise ValueError('Modeled interface is not on its device')
        for table in self.tables:
            if table.device_id not in ds: raise ValueError('Unknown routing table device')
            for route in table.routes:
                for hop in route.next_hops:
                    if hop.interface_id is not None: owned(table.device_id, hop.interface_id)
        for policy in self.policies:
            if policy.interface_id not in ifs: raise ValueError('Unknown policy interface')
        for flow in self.flows:
            if flow.source_device_id not in ds or flow.destination_device_id not in ds: raise ValueError('Unknown flow endpoint')
            for device, address, vrf in [(flow.source_device_id, flow.source_address, flow.vrf), (flow.destination_device_id, flow.destination_address, flow.destination_vrf)]:
                if not any(i.device_id == device and i.vrf == vrf and i.prefix and str(ipaddress.IPv4Interface(i.prefix).ip) == address for i in interfaces): raise ValueError('Flow address is not recorded in its endpoint VRF')
        for session in self.ospf:
            owned(session.left.device_id, session.left.interface_id); owned(session.right.device_id, session.right.interface_id)
        for session in self.bgp:
            if session.left.device_id not in ds or session.right.device_id not in ds: raise ValueError('Unknown BGP peer')
        for series in self.metrics:
            if series.device_id not in ds:raise ValueError('Unknown metric device')
            if series.interface_id is not None:owned(series.device_id,series.interface_id)
            if any(datetime.fromisoformat(p.timestamp.replace('Z','+00:00'))>logical_time for p in series.samples):raise ValueError('Future metric sample')


def recorded_protocol_model(values,timestamp):
    """Reuse session validation for an independently authored observation.

    Legacy one-ended notes remain notes; they cannot establish two-ended peer
    parameters. Structured records use the same contracts as the bounded model,
    without replacing or silently synchronizing that separate source.
    """
    if 'left' not in values and 'right' not in values:return None
    protocol=values.get('protocol')
    if protocol not in {'OSPF','BGP'}:raise ValueError('Structured protocol observation requires OSPF or BGP')
    session={key:value for key,value in values.items() if key not in {'protocol','session_id','source_category','observation_basis'}}
    session['id']=values.get('session_id')
    return NetworkModel.model_validate({'observed_at':timestamp,protocol.lower():[session]})


def policy_decision(model, interface, direction, vrf, flow):
    policies = [p for p in model.policies if p.interface_id == interface and p.direction == direction and p.vrf == vrf]
    if not policies: return ('permit', None) if model.policy_attachments_complete else ('unknown', 'Policy attachment completeness is unknown')
    policy = policies[0]
    for rule in policy.rules:
        if ipaddress.IPv4Address(flow.source_address) not in ipaddress.IPv4Network(rule.source) or ipaddress.IPv4Address(flow.destination_address) not in ipaddress.IPv4Network(rule.destination): continue
        if rule.protocol != 'ip' and rule.protocol != flow.protocol: continue
        if rule.source_port is not None and flow.source_port is None or rule.destination_port is not None and flow.destination_port is None:
            return 'unknown', policy.id + '/' + rule.id + ': flow port is unspecified'
        if rule.source_port is not None and flow.source_port != rule.source_port: continue
        if rule.destination_port is not None and flow.destination_port != rule.destination_port: continue
        return rule.action, policy.id + '/' + rule.id
    return policy.default_action, policy.id + '/default'


def forwarding(scenario, flow, *, max_hops=32, max_branches=16):
    """Enumerate declared forwarding alternatives; unknown is never success."""
    model = NetworkModel.model_validate(scenario['network'])
    ifs = {i['id']: i for i in scenario['interfaces']}
    names = {d['id']: d['hostname'] for d in scenario['devices']}
    tables = {(t.device_id, t.vrf): t for t in model.tables}
    def interface_location(interface, direction):
        return {'device_id':interface['device_id'],'hostname':names[interface['device_id']],
                'interface_id':interface['id'],'interface':interface['name'],'direction':direction,
                'admin_status':interface['admin_status'],'oper_status':interface['oper_status']}
    if not 1 <= max_hops <= 32 or not 1 <= max_branches <= 16: raise ValueError('Traversal budget exceeds supported bounds')
    def lookup(device, vrf, address, seen=()):
        key = (device, vrf, address)
        if key in seen or len(seen) >= max_hops: return [], 'recursive route loop or depth limit'
        table = tables.get((device, vrf))
        if not table: return [], 'routing table unavailable'
        matches = [r for r in table.routes if ipaddress.IPv4Address(address) in ipaddress.IPv4Network(r.prefix)]
        if not matches: return [], 'no route' if table.complete else 'routing table incomplete'
        # A present route in a partial table might be shadowed by a missing more-specific route.
        if not table.complete: return [], 'routing table incomplete'
        rank = lambda r: (-ipaddress.IPv4Network(r.prefix).prefixlen, r.preference, r.metric)
        best = min(rank(r) for r in matches); choices = []
        for route in (r for r in matches if rank(r) == best):
            if route.action != 'forward': choices.append((route, None, None)); continue
            for hop in route.next_hops:
                if hop.interface_id is not None: choices.append((route, hop, None)); continue
                resolved, error = lookup(device, vrf, hop.address, seen + (key,))
                if error: return [], error
                for _, resolved_hop, _ in resolved:
                    if resolved_hop is None: return [], 'recursive next hop does not resolve to a forwarding interface'
                    choices.append((route, NextHop(interface_id=resolved_hop.interface_id, address=hop.address, resolved=hop.resolved if hop.resolved is not None else resolved_hop.resolved), None))
        return choices, None

    for device, address, vrf in [(flow.source_device_id, flow.source_address, flow.vrf), (flow.destination_device_id, flow.destination_address, flow.destination_vrf)]:
        endpoints = [i for i in ifs.values() if i['device_id'] == device and i.get('vrf', 'default') == vrf and i.get('prefix') and str(ipaddress.IPv4Interface(i['prefix']).ip) == address]
        if len(endpoints) != 1 or endpoints[0]['admin_status'] != 'up' or endpoints[0]['oper_status'] != 'up':
            state = 'failed' if len(endpoints) == 1 and 'down' in {endpoints[0]['admin_status'], endpoints[0]['oper_status']} else 'unknown'
            return {'flow_id': flow.id, 'status': state, 'branches': [{'status': state, 'reason': 'Flow endpoint interface is down or not uniquely known up', 'hops': []}], 'modeled_only': True, 'scope': flow.model_dump(), 'encountered_device_ids': []}
    queue = deque([(flow.source_device_id, flow.vrf, None, [], set())]); outcomes = []; branches = 1
    encountered = set()
    while queue:
        device, vrf, ingress, steps, seen = queue.popleft()
        encountered.add(device)
        def finish(status, reason, trail=steps,location=None):
            # A trail records completed egress steps, not necessarily the device
            # where ingress/lookup stopped. Preserve that operand explicitly.
            if location is None and status != 'delivered':
                location={'device_id':device,'hostname':names[device],'vrf':vrf}
            outcomes.append({'status': status, 'reason': reason, 'hops': trail,
                **({'failure_location':location} if location else {}),
                **({'destination_ingress':{**interface_location(ifs[ingress],'ingress'),'vrf':vrf}}
                   if status=='delivered' and ingress is not None else {})})
        marker = (device, vrf, ingress)
        if marker in seen: finish('failed', 'forwarding loop'); continue
        if len(steps) >= max_hops: finish('unknown', 'hop budget reached'); continue
        if ingress is not None:
            state = ifs[ingress]
            if state['admin_status'] == 'down' or state['oper_status'] == 'down': finish('failed', 'ingress interface down',location=interface_location(state,'ingress')); continue
            if state['admin_status'] != 'up' or state['oper_status'] != 'up': finish('unknown', 'ingress interface state unknown',location=interface_location(state,'ingress')); continue
            action, rule = policy_decision(model, ingress, 'ingress', vrf, flow)
            if action != 'permit':
                finish('failed' if action == 'deny' else 'unknown','ingress policy '+str(rule),location={
                    'device_id':device,'hostname':names[device],'interface_id':ingress,'interface':state['name'],
                    'direction':'ingress','policy_rule':rule,'action':action})
                continue
        if device == flow.destination_device_id and vrf == flow.destination_vrf:
            finish('delivered', 'destination address reached in declared VRF'); continue
        choices, error = lookup(device, vrf, flow.destination_address)
        if error: finish('failed' if error == 'no route' else 'unknown', names[device] + ': ' + error); continue
        for number, (route, hop, _) in enumerate(choices):
            if number and branches >= max_branches: finish('unknown', 'branch budget reached'); break
            if number: branches += 1
            step = {'device_id': device, 'hostname': names[device], 'vrf': vrf, 'route_id': route.id, 'prefix': route.prefix}
            if ingress is not None:
                step['ingress']={**interface_location(ifs[ingress],'ingress'),'vrf':vrf}
            if route.action == 'discard': finish('failed', 'discard route', steps + [step]); continue
            if route.action == 'leak':
                queue.append((device, route.leak_to_vrf, None, steps + [step], seen | {marker})); continue
            interface = ifs[hop.interface_id]; step.update(interface=interface['name'], interface_id=interface['id'], next_hop=hop.address)
            trail = steps + [step]
            if interface.get('vrf', 'default') != vrf: finish('unknown', 'egress interface VRF mismatch', trail); continue
            if interface['admin_status'] == 'down' or interface['oper_status'] == 'down': finish('failed', 'egress interface down', trail,interface_location(interface,'egress')); continue
            if interface['admin_status'] != 'up' or interface['oper_status'] != 'up': finish('unknown', 'egress interface state unknown', trail,interface_location(interface,'egress')); continue
            action, rule = policy_decision(model, interface['id'], 'egress', vrf, flow)
            if action != 'permit':
                finish('failed' if action == 'deny' else 'unknown','egress policy '+str(rule),trail,location={
                    'device_id':device,'hostname':names[device],'interface_id':interface['id'],'interface':interface['name'],
                    'direction':'egress','policy_rule':rule,'action':action})
                continue
            if hop.resolved is not True: finish('failed' if hop.resolved is False else 'unknown', 'next-hop neighbor resolution failed' if hop.resolved is False else 'next-hop neighbor resolution unavailable', trail); continue
            peers = []
            for link in scenario['planned_links']:
                peer = link['dst_interface_id'] if link['src_interface_id'] == interface['id'] else link['src_interface_id'] if link['dst_interface_id'] == interface['id'] else None
                if peer is not None:
                    candidate = ifs[peer]
                    if candidate.get('prefix') and str(ipaddress.IPv4Interface(candidate['prefix']).ip) == (hop.address or flow.destination_address): peers.append(candidate)
            if len(peers) != 1: finish('unknown', 'no unique modeled adjacent next hop', trail); continue
            peer = peers[0]
            if not interface.get('prefix') or ipaddress.IPv4Interface(peer['prefix']).ip not in ipaddress.IPv4Interface(interface['prefix']).network or ipaddress.IPv4Interface(interface['prefix']).ip not in ipaddress.IPv4Interface(peer['prefix']).network:
                finish('failed', 'adjacent interface prefixes are not mutually on-link', trail); continue
            queue.append((peer['device_id'], peer.get('vrf', 'default'), peer['id'], trail, seen | {marker}))
    statuses = {o['status'] for o in outcomes}
    status = 'unknown' if 'unknown' in statuses else 'partial' if len(statuses) > 1 else 'delivered' if statuses == {'delivered'} else 'failed'
    return {'flow_id': flow.id, 'status': status, 'branches': outcomes, 'modeled_only': True,
            'encountered_device_ids': sorted(encountered),
            'scope': flow.model_dump(), 'budgets': {'hops': max_hops, 'branches': max_branches}}


def assess_flow(scenario, flow):
    forward = forwarding(scenario, flow)
    reverse = forwarding(scenario, flow.model_copy(update={'source_device_id': flow.destination_device_id,
        'destination_device_id': flow.source_device_id, 'source_address': flow.destination_address,
        'destination_address': flow.source_address, 'vrf': flow.destination_vrf, 'destination_vrf': flow.vrf,
        'source_port': flow.destination_port, 'destination_port': flow.source_port})) if flow.require_return else None
    states = [r['status'] for r in [forward, reverse] if r]
    status = 'unknown' if 'unknown' in states else 'partial' if 'partial' in states or len(set(states)) > 1 else states[0]
    return {'status': status, 'forward': forward, 'return': reverse,
            'limitation': 'Declared IPv4 stateless forwarding only; no NAT, IPv6, dynamic protocol emulation or physical packet test.'}


def protocol_findings(model):
    findings = []
    for session in model.ospf:
        a, b = session.left, session.right; issues = []
        for field in ['area', 'hello_seconds', 'dead_seconds', 'network_type']:
            if getattr(a, field) != getattr(b, field): issues.append(field + ' mismatch')
        missing=[];conditional=[]
        for field in ['authentication','area_type']:
            if getattr(a,field) is None or getattr(b,field) is None:missing.append(field)
            elif getattr(a,field)!=getattr(b,field):issues.append(field+' mismatch')
        if a.passive or b.passive: issues.append('passive interface')
        if a.router_id == b.router_id: issues.append('duplicate router ID')
        if a.mtu and b.mtu and a.mtu != b.mtu:
            if a.mtu_ignore is False and b.mtu_ignore is False:issues.append('MTU mismatch with both exceptions explicitly disabled')
            else:conditional.append('MTU differs; unknown or enabled MTU exceptions prevent treating this alone as an adjacency failure')
        benign = session.observed_state == '2-Way' and a.network_type == b.network_type == 'broadcast' and a.role == b.role == 'DROther'
        conflict = bool(issues and session.observed_state == 'Full')
        findings.append({'id': session.id, 'protocol': 'OSPF', 'devices': [a.device_id, b.device_id],
            'peer_parameters':[a.model_dump(exclude={'authentication'}),b.model_dump(exclude={'authentication'})],
            'observed_state': session.observed_state, 'configuration_differences': issues, 'conflict': conflict,
            'unknown_prerequisites':missing,'conditional_findings':conditional,
            'assessment': 'conflicting_evidence' if conflict else 'healthy_within_tested_scope' if not issues and (session.observed_state == 'Full' or benign) else 'strongly_supported' if issues and session.observed_state != 'unknown' else 'insufficient_evidence',
            'limitation': 'Neighbor observation and reviewed prerequisite comparisons; no LSDB convergence or complete protocol state machine.'})
    for session in model.bgp:
        a, b = session.left, session.right; issues = []
        if a.remote_as != b.local_as or b.remote_as != a.local_as: issues.append('neighbor remote AS differs from peer local AS')
        if a.shutdown or b.shutdown: issues.append('neighbor administratively shut down')
        if a.authentication is not None and b.authentication is not None and a.authentication != b.authentication: issues.append('authentication compatibility labels disagree')
        if not set(a.address_families) & set(b.address_families): issues.append('no common declared address family')
        if session.transport_reachable is False: issues.append('modeled transport is unreachable')
        conflict = bool(issues and session.observed_state == 'Established' and any('AS ' in s or 'shut down' in s or 'unreachable' in s for s in issues))
        findings.append({'id': session.id, 'protocol': 'BGP', 'devices': [a.device_id, b.device_id],
            'peer_parameters':[{**p.model_dump(exclude={'authentication','address'}),'local_address':p.address,'neighbor_address':other.address} for p,other in [(a,b),(b,a)]],
            'session_type':'ibgp' if a.local_as==b.local_as else 'ebgp',
            'observed_state': session.observed_state, 'configuration_differences': issues, 'conflict': conflict,
            'accepted_prefixes': session.accepted_prefixes, 'rejected_prefixes': session.rejected_prefixes,
            'policy_observed': session.policy_observed,
            **{field:getattr(session,field) for field in ['received_prefixes','advertised_prefixes','withdrawn_prefixes','rib_in_complete','rib_out_complete','next_hop_valid']},
            'assessment': 'conflicting_evidence' if conflict else 'strongly_supported' if issues and session.observed_state != 'unknown' else 'healthy_within_tested_scope' if session.observed_state == 'Established' else 'insufficient_evidence',
            'limitation': 'Session health does not establish prefix acceptance, full best-path behavior or end-to-end forwarding.'})
    return findings


def metric_findings(model,interfaces):
    """Counter/rate arithmetic and qualified correlation, never unique causation."""
    results=[];ifs={i['id']:i for i in interfaces}
    for series in model.metrics:
        points=series.samples;missing=any(p.value is None for p in points)
        times=[datetime.fromisoformat(p.timestamp.replace('Z','+00:00')) for p in points]
        gaps=any((b-a).total_seconds()>series.sampling_seconds*1.5 for a,b in zip(times,times[1:]))
        notes=[];values={'metric':series.metric,'unit':series.unit,'sampling_seconds':series.sampling_seconds,'samples':[p.model_dump() for p in points],
            'sampling_gaps':gaps,'missing_values':missing,'window_start':points[0].timestamp,'window_end':points[-1].timestamp}
        if missing:notes.append('Samples are missing; absence is not zero')
        elif series.unit=='count':
            reset=any(b.value<a.value for a,b in zip(points,points[1:]))
            values['counter_reset_or_wrap']=reset
            if len(points)<2:notes.append('A single cumulative counter does not establish a current rate or trend')
            elif reset:notes.append('Counter decreased; rate cannot be derived across reset/wrap')
            else:
                delta=points[-1].value-points[0].value;seconds=(times[-1]-times[0]).total_seconds()
                values.update(delta=delta,average_per_second=delta/seconds)
                notes.append('Counter increased within this sampling window' if delta>0 else 'No increase within this sampling window')
        elif series.unit=='bps' and series.interface_id and ifs[series.interface_id].get('speed_bps'):
            values['peak_utilization_pct']=max(p.value for p in points)/ifs[series.interface_id]['speed_bps']*100
            notes.append('Directional measured traffic compared with the declared line rate')
        if gaps:notes.append('Sampling gaps limit continuity claims')
        results.append({'id':series.id,'device_id':series.device_id,'interface_id':series.interface_id,
            'timestamp':points[-1].timestamp,'values':values,'notes':notes})
    for row in results:
        values=row['values'];utilization=values.get('peak_utilization_pct')
        if utilization is not None and utilization>100:
            row['notes'].append('Traffic exceeds declared line rate; check measurement scope, units or observer conflict')
        elif utilization is not None and utilization>=90 and not values['sampling_gaps'] and not values['missing_values']:
            drops=[other for other in results if other['device_id']==row['device_id'] and other['interface_id']==row['interface_id']
                   and other['values']['metric'] in {'discards','queue_drops'} and other['values'].get('delta',0)>0
                   and not other['values']['sampling_gaps'] and other['values']['window_start']==values['window_start'] and other['values']['window_end']==values['window_end']]
            if drops:
                values['congestion_hypothesis']='plausible';values['correlated_source_ids']=[r['id'] for r in drops]
                row['notes'].append('High utilization and increasing drops share a window; congestion is plausible, not uniquely established')
    return results

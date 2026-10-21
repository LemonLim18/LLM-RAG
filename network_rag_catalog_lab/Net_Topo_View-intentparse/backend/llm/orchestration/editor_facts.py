"""Bounded literal IOS-style evidence checks, not a network configuration parser.

Only explicit command families and direct factual paraphrases are checked. This
does not establish effective configuration, reachability or vendor compatibility.
"""
import ipaddress
import re

IP = r'(?:\d{1,3}\.){3}\d{1,3}'
INTERFACE = r'(?:GigabitEthernet|TenGigabitEthernet|FastEthernet|Ethernet|Loopback|Vlan|Port-channel|Serial)[\w/.:\-]+'


def literal_facts(documents, path):
    facts = {'local_as': set(), 'neighbors': {}, 'interfaces': {}, 'routes': {}, 'hostnames':set(), 'lines': []}
    for document in documents:
        if document.get('source') != path: continue
        scope = None
        for number, line in enumerate(document.get('text', '').splitlines(), document.get('start_line', 1)):
            command = line.strip()
            if match:=re.fullmatch(r'hostname\s+(\S+)',command,re.I):facts['hostnames'].add(match[1])
            if not line[:1].isspace(): scope = None
            if match := re.fullmatch(r'router bgp (\d+(?:\.\d+)?)', command, re.I):
                facts['local_as'].add(match[1]); scope = 'bgp'
            elif match := re.fullmatch(r'interface (\S+)', command, re.I):
                scope = match[1]; facts['interfaces'].setdefault(scope.lower(), set())
            elif scope == 'bgp' and (match := re.fullmatch(r'neighbor (' + IP + r') remote-as (\d+(?:\.\d+)?)', command, re.I)):
                facts['neighbors'].setdefault(match[1], set()).add(match[2])
            elif scope and scope.lower() in facts['interfaces']:
                if match := re.fullmatch(r'ip address (' + IP + r') (' + IP + r')(?: secondary)?', command, re.I):
                    try: facts['interfaces'][scope.lower()].add(str(ipaddress.IPv4Interface(match[1] + '/' + match[2])))
                    except ValueError: pass
            if match := re.fullmatch(r'ip route (' + IP + r') (' + IP + r') (' + IP + r')(?: \d+)?', command, re.I):
                try: facts['routes'].setdefault(str(ipaddress.IPv4Network(match[1]+'/'+match[2], strict=False)), set()).add(match[3])
                except ValueError: pass
            if re.match(r'(?:router bgp |interface |ip route |neighbor .* remote-as |ip address )', command, re.I):
                facts['lines'].append((number, line))
    return facts


def contradicted_claims(answer, facts):
    invalid = []
    # A document line number is not a named router. Check only explicitly
    # attributed identities when a literal hostname is actually present.
    if facts.get('hostnames'):
        for name in re.findall(r'\b(?:on|for)\s+(?:the\s+)?(?:router|device)\s+([A-Za-z0-9][\w-]*)',re.sub(r'[*`]','',answer),re.I):
            if name.lower() not in {'with','that','which','whose','itself','in','as','is','to','and'} and name.casefold() not in {value.casefold() for value in facts['hostnames']}:
                invalid.append('configured hostname identity')
    interface_scope = None
    peer_scope = []
    for raw in answer.splitlines():
        line = re.sub(r'[*`#]', '', raw).strip()
        # Advice, examples, questions and uncertainty are not recorded-state claims.
        if re.search(r'\b(could|might|example|recommend|would|should|consider|if|unknown|not established)\b|\?$', line, re.I): continue
        names = re.findall(INTERFACE, line, re.I)
        if names: interface_scope = names[0].lower()
        elif re.search(r'\b(router|OSPF|BGP|static route)\b', line, re.I): interface_scope = None
        if facts['local_as']:
            for value in re.findall(r'\blocal\s+(?:AS|autonomous system)(?:\s+(?:number|is|of))*\s*[:=]?\s*(\d+(?:\.\d+)?)', line, re.I):
                if value not in facts['local_as']: invalid.append('local AS')
        if facts['neighbors']:
            addresses = re.findall(IP, line)
            peers = [value for value in addresses if value in facts['neighbors']]
            # An OSPF router ID earlier in a compound comparison is not a BGP
            # neighbor address. Bind identity checks to the neighbor clause.
            for clause in re.split(r';|\b(?:while|whereas|but)\b',line,flags=re.I):
                if not re.search(r'\bneighbor\b',clause,re.I):continue
                neighbor_addresses=re.findall(IP,clause)
                if neighbor_addresses and not any(value in facts['neighbors'] for value in neighbor_addresses):invalid.append('neighbor identity')
            if peers: peer_scope = peers
            remote = re.findall(r'\b(?:remote[- ]?(?:AS|autonomous system)|(?:with|in) AS)(?:\s+(?:number|is|of))*\s*[:=]?\s*(\d+(?:\.\d+)?)', line, re.I)
            attributed = peers or peer_scope or list(facts['neighbors'])
            if attributed:
                allowed = set().union(*(facts['neighbors'][value] for value in attributed))
                if any(value not in allowed for value in remote): invalid.append('neighbor remote AS')
        if facts['interfaces'] and interface_scope and re.search(r'\b(address|IP|ip address)\b', line, re.I):
            expected = facts['interfaces'].get(interface_scope)
            if expected is None: invalid.append('interface identity')
            else:
                literal = re.search(r'\bip address ('+IP+r') ('+IP+r')', line, re.I)
                if literal:
                    try:
                        if str(ipaddress.IPv4Interface(literal[1]+'/'+literal[2])) not in expected: invalid.append('interface address/mask')
                    except ValueError: invalid.append('interface address/mask')
                for match in re.finditer(IP + r'(?:/\d{1,2})?', line):
                    value=match[0]
                    if literal and match.start() in (literal.start(1),literal.start(2)): continue
                    if re.search(r'\b(?:netmask|mask)\s*[:=]?\s*$',line[:match.start()],re.I):
                        if value not in {str(ipaddress.IPv4Interface(x).netmask) for x in expected}: invalid.append('interface mask')
                        continue
                    allowed = expected if '/' in value else {x.split('/')[0] for x in expected}
                    if value not in allowed: invalid.append('interface address')
        if facts['routes'] and re.search(r'\b(?:static|route)\b', line, re.I):
            prefixes = re.findall(IP + r'/\d{1,2}', line)
            hops = re.findall(r'\b(?:via|next[- ]hop)(?:\s+(?:is|of|:|=))*\s*(' + IP + ')', line, re.I)
            if prefixes and hops:
                for prefix in prefixes:
                    if prefix not in facts['routes'] or any(hop not in facts['routes'][prefix] for hop in hops): invalid.append('static route next hop')
    # A buffer, including a saved one, cannot establish installed or live state.
    if re.search(r'\b(?:is|are|currently)\s+(?:successfully\s+)?(?:deployed|installed|operational|live|reachable)\b', answer, re.I):
        invalid.append('device state')
    if re.search(INTERFACE + r'\s+(?:is|currently)\s+(?:up|down)\b', answer, re.I): invalid.append('interface operational state')
    return sorted(set(invalid))

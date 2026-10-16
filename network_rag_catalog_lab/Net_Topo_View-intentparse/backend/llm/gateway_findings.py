"""Deterministic release boundary for investigations with no observations."""


def empty_observation_answer(context):
    operational = [item for item in context if item.get('tool') in {
        'network.telemetry', 'network.syslog', 'network.incidents', 'network.configuration'}]
    if not operational:
        return None

    def has_records(data):
        if not isinstance(data, dict):
            return False
        # Truncated data cannot establish absence. Let normal synthesis handle it.
        return bool(data.get('records') or data.get('excerpt') or any(
            has_records(source.get('data')) for source in data.get('sources', [])))

    if any(has_records(item.get('data')) for item in operational):
        return None
    names = {'network.telemetry': 'Measurements', 'network.syslog': 'Syslogs',
             'network.incidents': 'Incident history', 'network.configuration': 'Configuration history'}
    lines = ['No matching operational records were returned for this request.']
    for item in operational:
        state = 'Access denied' if item['status'] == 'denied' else 'Reader failed' if item['status'] == 'error' else 'No matching records available'
        lines.append('- **' + names[item['tool']] + ':** ' + state + '.')
    topology = next((item.get('data') or {} for item in context if item.get('tool') == 'network.topology'), {})
    if topology.get('topology_kind') == 'planned':
        lines.append('- **Planned topology:** ' + str(topology.get('total_links', 0)) + ' recorded link(s) in the selected scope; packet reachability was not measured.')
    lines.extend(['', 'Missing records do not establish a fault, healthy operation, or an authorization failure. No network root cause can be established from this result.',
                  'To investigate further, supply timestamped measurements, relevant logs or configuration captures for the affected device and time range.'])
    return '\n'.join(lines)

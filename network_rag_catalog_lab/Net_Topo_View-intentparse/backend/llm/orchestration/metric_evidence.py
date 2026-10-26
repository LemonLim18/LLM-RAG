"""Relationships between already-authorized metric records and calculations.

No reader, interpolation, model call or general network parser lives here.
Claims are checked only for the typed calculation fields offered by readers.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from itertools import combinations
import re


def _stamp(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError, OverflowError):
        return None


def metric_conflicts(facts):
    """Expose disagreements at the same scope, unit and observation instant."""
    units = {'bits_per_second': 'bps', '%': 'percent'}
    groups = {}
    for fact in facts:
        key = (fact.get('device'), fact.get('interface'), fact['metric'],
               units.get(fact.get('unit'), fact.get('unit')))
        groups.setdefault(key, []).append(fact)
    conflicts = []
    for scope, series in groups.items():
        for left, right in combinations(series, 2):
            points = {_stamp(p['timestamp']): p for p in left['samples']
                      if p.get('value') is not None and _stamp(p['timestamp']) is not None}
            differing = []
            for point in right['samples']:
                other = points.get(_stamp(point['timestamp']))
                if other is not None and point.get('value') is not None and other['value'] != point['value']:
                    differing.append({'timestamp': point['timestamp'],
                                      'left_value': other['value'], 'right_value': point['value']})
            if differing:
                conflicts.append({'device': scope[0], 'interface': scope[1], 'metric': scope[2],
                                  'unit': scope[3], 'record_refs': [left['record_ref'], right['record_ref']],
                                  'source_categories': [left.get('source_category'), right.get('source_category')],
                                  'points': differing})
    return conflicts


def metric_calculation_claim_errors(answer, facts):
    """Bind explicit calculated quantities to their own device/port records.

    This does not certify arbitrary causal prose. Sampling cadence and window
    duration are different typed quantities even when both are in seconds.
    """
    number = r'(-?\d+(?:\.\d+)?)'
    patterns = [
        ('peak_utilization_pct', r'\b(?:peak\s+)?(?:directional\s+)?utili[sz]ation\s*(?:of|is|was|:|=)?\s*' + number + r'\s*(%|percent)(?!\w)'),
        ('sampling_seconds', r'\bsampl(?:ing|e)\s+(?:interval|period|cadence)\s*(?:of|is|was|:|=)?\s*' + number + r'[- ]*(seconds?|minutes?)\b'),
        ('window_duration', number + r'[- ]*(seconds?|minutes?)[- ]+window\b'),
        ('window_duration', r'\bwindow\s*(?:(?:length|duration)\s*)?(?:of|is|was|:|=)?\s*' + number + r'[- ]*(seconds?|minutes?)\b'),
        ('average_per_second', number + r'\s*(counts?\s*(?:/|per\s+)\s*(?:second|sec|s)\b)'),
    ]
    scopes = {(f.get('device'), f.get('interface')) for f in facts}
    errors = []
    carried_device = None
    for clause in re.split(r'(?<=[.!?])\s+|\n|;\s*', re.sub(r'[*`]', '', answer)):
        for field, pattern in patterns:
            for match in re.finditer(pattern, clause, re.I):
                before,after=clause[max(0,match.start()-35):match.start()],clause[match.end():]
                if (re.search(r'\b(?:not|unknown|unverified|unestablished)\s*(?:a\s+)?$',before,re.I)
                        or re.match(r'\s*(?:is\s+)?(?:not (?:established|verified)|unknown|unverified)\b',after,re.I)):
                    continue
                prefix = clause[:match.start()]
                named = [(prefix.casefold().rfind(str(f['device']).casefold()), f['device'])
                         for f in facts if f.get('device') and str(f['device']).casefold() in prefix.casefold()]
                device = max(named)[1] if named else carried_device
                selected = [f for f in facts if device is None or f.get('device') == device]
                explicit_refs = [f for f in selected if f['record_ref'] in clause]
                if explicit_refs:
                    selected = explicit_refs
                ports = {f.get('interface') for f in selected if f.get('interface') and f['interface'] in prefix}
                if ports:
                    selected = [f for f in selected if f.get('interface') in ports]
                selected_scopes = {(f.get('device'), f.get('interface')) for f in selected}
                if (device is None and len(scopes) > 1 and not explicit_refs) or len(selected_scopes) > 1:
                    errors.append('Attribute the calculation to its recorded device/interface or record reference; shared numbers do not establish ownership')
                    continue
                allowed = []
                for fact in selected:
                    values = fact.get('calculations', {})
                    if field == 'window_duration':
                        start, end = _stamp(values.get('window_start')), _stamp(values.get('window_end'))
                        if start is not None and end is not None:
                            allowed.append(end-start)
                    elif values.get(field) is not None:
                        allowed.append(values[field])
                    elif (field == 'peak_utilization_pct' and fact.get('unit') in {'percent','%'}
                          and not re.search(r'\bpeak\b', match[0], re.I)):
                        # A measured percentage gauge is already a quantity in
                        # percent. It is distinct from deriving utilization
                        # from a traffic series and a declared line capacity.
                        allowed.extend(p['value'] for p in fact['samples'] if p.get('value') is not None)
                try:
                    claimed = Decimal(match[1]) * (60 if match[2].lower().startswith('minute') else 1)
                    matches = any(abs(claimed-Decimal(str(v))) <= Decimal('0.000001') for v in allowed)
                except (InvalidOperation, ValueError):
                    matches = False
                if not matches:
                    errors.append('The claimed '+field+' is not a returned calculation for that device/interface; do not borrow another series or confuse sampling cadence with window duration')
        named = [(clause.casefold().rfind(str(f['device']).casefold()), f['device'])
                 for f in facts if f.get('device') and str(f['device']).casefold() in clause.casefold()]
        if named:
            carried_device = max(named)[1]
    for fact in facts:
        if not fact.get('calculations',{}).get('counter_reset_or_wrap'):
            continue
        values=[p['value'] for p in fact['samples'] if p.get('value') is not None]
        for clause in re.split(r'(?<=[.!?])\s+|\n',answer):
            if re.search(r'\b(?:may|might|could|can|possible|unknown|not established|not recorded)\b',clause,re.I):continue
            if re.search(r'\breset\w*\b.{0,90}\b(?:every|after|period|interval|typically|threshold)\b',clause,re.I):
                errors.append('A sampled counter discontinuity does not establish a reset schedule, threshold or cause; sampling cadence is not a reset timer')
            if 0 not in values and re.search(r'\breset\w*\s+to\s+(?:zero|0)\b',clause,re.I):
                errors.append('The returned counter samples do not record a reset-to-zero value')
        if len(values)<3:
            continue
        if (any(b>a for a,b in zip(values,values[1:]))
                and re.search(r'\b(?:steady|continuous|monotonic)\s+decreas\w*\b',answer,re.I)):
            errors.append('The recorded counter has an increase after a decrease/reset; it does not establish a monotonic decrease through the window')
    return list(dict.fromkeys(errors))

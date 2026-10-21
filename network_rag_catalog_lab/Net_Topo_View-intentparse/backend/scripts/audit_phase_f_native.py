"""Read-only Phase F native matrix and independent corrected-output replay.

Reuses V9 snapshots/renderer; writes only reports. Branch counts describe scope,
not proof of universal command semantics or complete branch coverage.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/local_providers'), str(ROOT.parent / 'network_rag_catalog_v2')]


def audit(output, reconcile=False):
    from jinja2 import Environment, nodes
    from local_providers.knowledge_lifecycle import pointer_for, guard_native_renderer
    from local_providers.knowledge_review import identity
    from app.knowledge.runtime import snapshot_scope
    from scripts.phase_f_native_corrections import SCOPE, independent_fixtures
    base = ROOT / 'backend/knowledge_workspace/storage/catalog_releases'
    active_bytes = (base / 'active.json').read_bytes()
    active = json.loads(active_bytes)
    _, snapshot = pointer_for(base, active['release_id'])
    _, previous = pointer_for(base, 'f0e33c357dd54988ba7e651d813c76a7')
    reviews = {r['identity']: r for r in snapshot.read_json(snapshot.manifest['cognishield_engineer_reviews']['artifact_path'])['bindings']}
    old_bindings = {identity(b): b for b in previous.manifest['template_bindings']}
    renderer = guard_native_renderer()
    rows = []
    with snapshot_scope(snapshot):
        for binding in snapshot.manifest['template_bindings']:
            key = identity(binding)
            review = reviews[key]
            source = (snapshot.root / binding['artifact_path']).read_text(encoding='utf-8')
            ast = Environment().parse(source)
            fixed = (binding['operation_id'], binding['vendor']) in SCOPE
            independent = []
            if fixed:
                for fixture in independent_fixtures(binding['operation_id'], binding['vendor']):
                    actual = renderer({'hostname': 'CONTROLLED-PHASE-F-READONLY', 'vendor': binding['vendor'], 'platform': binding['platform'], 'version': binding['versions'][0]}, binding['operation_id'], fixture['parameters'])
                    assert actual.strip() == fixture['expected_output'].strip(), (key, actual, fixture)
                    independent.append({'parameters': fixture['parameters'], 'expected': fixture['expected_output'], 'actual': actual, 'status': 'PASS'})
            method = review['method']
            conditions = len(list(ast.find_all(nodes.If)))
            loops = len(list(ast.find_all(nodes.For)))
            rows.append({'identity': key, 'operation_id': binding['operation_id'], 'vendor': binding['vendor'],
                'platform': binding['platform'], 'versions': binding['versions'], 'active_release': active['release_id'],
                'template_sha256': sha256(source.encode()).hexdigest(),
                'changed_since_phase_e': binding['template_sha256'] != old_bindings[key]['template_sha256'],
                'publication_authorization': review['approval']['approval_authority'],
                'publication_actor': review['approval']['approved_by'], 'publication_action': review['approval'].get('approval_action'),
                'implementation_status': 'ENGINEER_PUBLISHED_ACTIVE_RENDER_TESTED',
                'conditional_blocks': conditions, 'loops': loops,
                'optional_fields': sorted(binding['input_contract'].get('optional_defaults', {})),
                'representative_fixtures': len(method['fixtures']), 'compiled_checks': review['checks']['status'],
                'negative_fixtures': sum(r['kind'] == 'negative' and r['passed'] for r in review['checks']['results']),
                'runtime_profiles': review['runtime_checks']['profiles'],
                'independent_corrected_statement_fixtures': independent,
                'branch_coverage': 'CORRECTED_STATEMENT_BRANCHES_TESTED' if fixed else 'REPRESENTATIVE_ONLY' if conditions or loops else 'NO_CONDITIONAL_BLOCKS',
                'studio_journey': 'NOT_RUN_PHASE_F', 'vendor_device_certification': review['certifications']})
    assert len(rows) == len({r['identity'] for r in rows}) == 141
    assert sum(r['changed_since_phase_e'] for r in rows) == 4
    assert all(r['compiled_checks'] == 'PASS' for r in rows)
    assert (base / 'active.json').read_bytes() == active_bytes
    result = {'format_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(), 'active_release': active,
        'rollback': previous.release_id, 'bindings': 141, 'source_changes': 4,
        'independent_current_host_replays': sum(len(r['independent_corrected_statement_fixtures']) for r in rows),
        'scope': 'All published metadata/compiled fixtures; 12 independent corrected-family actual V9 replays. Not device certification or 141 Studio journeys.',
        'remaining': ['Risk-family independent spot oracles and expanded proportional branch coverage beyond corrected families.', 'All 141 real-service Studio journeys.'], 'rows': rows}
    dest = (ROOT / output).resolve()
    if not dest.is_relative_to(ROOT.resolve()):
        raise ValueError('Report must remain within workspace')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('x', encoding='utf-8', newline='\n') as file:
        json.dump(result, file, indent=2)
    if reconcile:
        path = ROOT / 'docs/evaluations/phase_e_vendor_progress.json'
        ledger = json.loads(path.read_text())
        for row in ledger['candidates']:
            current = next(r for r in rows if r['identity'] == row['identity'])
            history = row.setdefault('preparation_history', [])
            prior = {k: row.get(k) for k in ['implementation_status', 'active_release_id', 'fingerprint', 'template_sha256', 'publication_timestamp']}
            if prior not in history:
                history.append(prior)
            review = reviews[row['identity']]
            row.update(implementation_status=current['implementation_status'], ordinary_active=True,
                active_release_id=active['release_id'], fingerprint=review['fingerprint'], template_sha256=current['template_sha256'],
                positive_fixtures=current['representative_fixtures'], negative_fixtures=current['negative_fixtures'],
                publication_actor=current['publication_actor'], publication_action=current['publication_action'],
                publication_timestamp=review['approval']['approved_at'],
                phase_f_branch_coverage=current['branch_coverage'])
        ledger['ordinary_active_release'] = active['release_id']
        ledger['updated_at'] = result['checked_at']
        with path.open('w', encoding='utf-8', newline='\n') as file:
            json.dump(ledger, file, indent=2)
            file.write('\n')
    print(json.dumps({'artifact': str(dest), 'release': active, 'bindings': 141, 'independent_replays': 12, 'changed_sources': 4, 'ledger_reconciled': reconcile}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='docs/evaluations/phase_f_native_output_audit.json')
    parser.add_argument('--reconcile-phase-e-ledger', action='store_true')
    args = parser.parse_args()
    audit(args.output, args.reconcile_phase_e_ledger)

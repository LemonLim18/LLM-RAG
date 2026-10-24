"""Real gateway continuity and scanned-PDF acceptance in the reused G7 workspace.

Run seed and resume as separate OS processes. Expectations and uploaded bytes
are retained; no model, extraction or history is substituted. Not a fresh quality
benchmark, and no ordinary application database or saved editor file is changed.
"""
import argparse
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
OWNER = 'G9-CONTINUITY-OWNER'
OLD_IP, NEW_IP = '10.88.1.2', '192.0.2.88'
SCAN_TEXT = ['Scanned engineering note', 'Device: G9-Edge', 'OSPF process: 88',
             'Hello interval: 12 seconds', 'Dead interval: 48 seconds',
             'These are proposed settings, not a device measurement.']


def render_scan():
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (1700, 650), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 38)
    for index, line in enumerate(SCAN_TEXT):
        draw.text((60, 50 + index * 85), line, font=font, fill='black')
    from io import BytesIO
    output = BytesIO(); image.save(output, format='PDF', resolution=150)
    print(json.dumps({'pdf': base64.b64encode(output.getvalue()).decode()}))


async def main(args):
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router
    from llm.gateway_store import ensure_schema
    from local_providers.development import ScenarioManager
    from scripts.phase_d_audit import Run, source_manifest

    os.environ.update(COGNISHIELD_AI_ENGINE='langgraph_b3', COGNISHIELD_AI_PLANNING='1',
                      COGNISHIELD_AI_SYNTHESIS='1', COGNISHIELD_DEV_SIMULATION='0')
    previous = (ROOT / args.resume).resolve()
    assert previous.is_relative_to((ROOT / 'tmp/phase-g/iterations').resolve())
    workspace = Path(json.loads((previous / 'workspace-ref.json').read_text(encoding='utf-8'))['path']).resolve()
    assert workspace.is_relative_to((ROOT / 'tmp').resolve()) and (workspace / 'app.db').is_file()
    spec = ROOT / {'normal':'docs/evaluations/phase_g_continuity_normal_v2.json',
                   'config':'docs/evaluations/phase_g_uploaded_config_v3.json'}.get(args.phase,
                   'docs/evaluations/phase_g_continuity_cases_v1.json')
    run = Run('G9-continuity-' + args.phase, 'real_model_full_agent', {
        'model': 'qwen2.5:1.5b', 'source_manifest': source_manifest(), 'phase': args.phase,
        'specification_sha256': hashlib.sha256(spec.read_bytes()).hexdigest(),
        'fresh_holdout': False, 'process_id': os.getpid(), 'workspace': str(workspace),
        'no_ordinary_database_or_device_actions': True}, phase='phase-g')
    db = DatabaseManager(str(workspace / 'app.db')); db.initialize(); ensure_schema(db)
    db._development_scenario = ScenarioManager(workspace / 'g9-ordinary-recovery-state.json', enabled_default=False)
    assert not db._development_scenario.is_enabled()
    app = FastAPI(); app.state.local_db = db; app.include_router(router)
    references = workspace / 'g9-continuity-reference.json'
    outcomes = []
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://continuity',
                headers={'Authorization': 'Bearer ' + create_access_token(941, OWNER, 'engineer')}, timeout=240) as client:
            async def call(method, path, body=None):
                response = await client.request(method, path, json=body)
                response.raise_for_status(); return response.json()

            async def ask(cid, name, prompt, required, predicate, attachments=None):
                started = time.monotonic(); result = None; error = None
                try:
                    result = await call('POST', '/api/v1/ai/conversations/' + cid + '/turns', {
                        'request_id': str(uuid4()), 'prompt': prompt, 'model': 'qwen2.5:1.5b',
                        **({'attachment_ids': attachments} if attachments else {})})
                    tools = {item['tool'] for item in result.get('observations', [])}
                    if result.get('context_coverage', {}).get('files', {}).get('tool') == 'document.read':
                        tools.add('document.read')
                    assert tools == set(required), 'Wrong authorized source selection: ' + str(tools)
                    assert not result.get('proposal') and not result.get('preview'), 'Unexpected engineering workflow'
                    assert result['status'] == 'success' and predicate(result), 'Expected content/context not established'
                except Exception as exc:
                    error = type(exc).__name__ + ': ' + str(exc)
                ok = error is None; outcomes.append(ok)
                run.record(name, 'PASS' if ok else 'FAIL', prompt=prompt,
                    expected={'tools': required, 'effect': 'read only', 'full_answer_review': 'still required'},
                    actual={'conversation': cid, 'result': result, 'error': error},
                    classification=None if ok else 'source_context_or_content_failure',
                    latency_ms=round((time.monotonic() - started) * 1000, 2))
                print(json.dumps({'case': name, 'pass': ok, 'error': error, 'run': str(run.path)}), flush=True)
                return result, ok

            if args.phase == 'seed':
                if references.exists():
                    raise RuntimeError('Seed reference already exists; preserve it and use resume')
                with db._connect() as c:
                    assert not c.execute('SELECT 1 FROM devices WHERE id=91002').fetchone()
                    c.execute("INSERT INTO devices(id,hostname,vendor,management_ip,source) VALUES(91002,'G9-Edge','cisco_ios','198.18.88.2','controlled-evaluation')")
                    for iid, name, ip in [(91011, 'GigabitEthernet0/1', OLD_IP), (91012, 'GigabitEthernet0/2', '10.88.2.2')]:
                        c.execute('INSERT INTO interfaces(id,device_id,name,ip_address) VALUES(?,91002,?,?)', (iid, name, ip))
                refs = {'seed_run': str(run.path), 'process_id': os.getpid(), 'conversations': {}}
                for surface in ['floating', 'studio']:
                    cid = (await call('POST', '/api/v1/ai/conversations', {'assistant_kind': surface}))['id']
                    _, ok = await ask(cid, 'G9-MEMORY-LIST-' + surface,
                        'What interfaces are recorded for G9-Edge? Include their IP addresses.', ['inventory.read'],
                        lambda value: all(token in value['answer'] for token in ['GigabitEthernet0/1', OLD_IP, 'GigabitEthernet0/2', '10.88.2.2']))
                    refs['conversations'][surface] = {'id': cid, 'seed_pass': ok}
                references.write_text(json.dumps(refs, indent=2), encoding='utf-8')
            elif args.phase == 'resume':
                refs = json.loads(references.read_text(encoding='utf-8'))
                assert refs['process_id'] != os.getpid(), 'Resume must run in a fresh OS process'
                assert all(row['seed_pass'] for row in refs['conversations'].values()), 'Seed did not establish actual reference context'
                for surface, row in refs['conversations'].items():
                    await ask(row['id'], 'G9-MEMORY-RESTART-' + surface,
                        'What is the IP address of the first one?', ['inventory.read'],
                        lambda value: OLD_IP in value['answer'] and value['context_coverage']['agent']['checkpointing'] == 'restored')
                with db._connect() as c:
                    assert c.execute('SELECT ip_address FROM interfaces WHERE id=91011').fetchone()[0] == OLD_IP
                    c.execute('UPDATE interfaces SET ip_address=? WHERE id=91011', (NEW_IP,))
                for surface, row in refs['conversations'].items():
                    await ask(row['id'], 'G9-MEMORY-REFRESH-' + surface,
                        'Are you sure? Check that interface\'s recorded address again.', ['inventory.read'],
                        lambda value: NEW_IP in value['answer'] and 'GigabitEthernet0/1' in value['answer'])
                    await ask(row['id'], 'G9-MEMORY-TOPIC-' + surface,
                        'New topic: what is 8 plus 6?', [],
                        lambda value: '14' in value['answer'] and not value['evidence'])
                    denied = await client.get('/api/v1/ai/conversations/' + row['id'], headers={
                        'Authorization': 'Bearer ' + create_access_token(942, 'OTHER-CONTINUITY-OWNER', 'engineer')})
                    assert denied.status_code == 404
            elif args.phase == 'scanned':
                from llm.validation_process import bounded_process
                executable = os.getenv('COGNISHIELD_DOCUMENT_PYTHON')
                if not executable:
                    raise RuntimeError('Use the configured document interpreter; no library installation is authorized')
                output = bounded_process([executable, '-I', '-B', str(Path(__file__).resolve()), '--render-scan'], '', timeout=20)
                if output.returncode:
                    raise RuntimeError('Existing document runtime could not render scan: ' + output.stderr[:500])
                raw = base64.b64decode(json.loads(output.stdout)['pdf'], validate=True)
                assert raw.startswith(b'%PDF') and len(raw) < 2 * 1024 * 1024
                (run.path / 'scanned-note.pdf').write_bytes(raw)
                for surface in ['floating', 'studio']:
                    cid = (await call('POST', '/api/v1/ai/conversations', {'assistant_kind': surface}))['id']
                    response = await client.post('/api/v1/ai/conversations/' + cid + '/attachments', content=raw,
                                                headers={'X-File-Name': 'g9-scanned-note.pdf'})
                    response.raise_for_status(); attachment = response.json()['id']
                    with db._connect() as c:
                        row = c.execute('SELECT segments FROM ai_attachments WHERE id=? AND conversation_id=?', (attachment, cid)).fetchone()
                    segments = json.loads(row[0]); (run.path / (surface + '-actual-extraction.json')).write_text(json.dumps(segments, indent=2), encoding='utf-8')
                    extracted = json.dumps(segments)
                    assert all(word in extracted for word in ['OSPF', '88', '12', '48']), 'The actual scanned content was not extracted'
                    await ask(cid, 'G9-SCANNED-CONTENT-' + surface,
                        'What OSPF process and timer values appear on page 1 of the scanned PDF? Explain its actual content.',
                        ['document.read'], lambda value: all(word in value['answer'] for word in ['88', '12', '48'])
                        and any(e.get('page') == 1 for e in value['evidence']), [attachment])
                    await ask(cid, 'G9-SCANNED-FOLLOWUP-' + surface,
                        'Does that page describe proposed settings or an actual device measurement?', ['document.read'],
                        lambda value: 'propos' in value['answer'].lower() and any(e.get('page') == 1 for e in value['evidence']))
            elif args.phase == 'normal':
                import lab_config
                from datetime import datetime, timezone
                from local_providers.observations import JsonObservations
                poison = workspace / 'g9-prohibited-normal-fixtures'; poison.mkdir(exist_ok=True)
                fixture = {'version': 1, 'devices': [{'device_id': 91002, 'metrics': [{
                    'time': datetime.now(timezone.utc).isoformat(), 'cpu': 97.375, 'memory': 29.625}]}]}
                (poison / 'observations.json').write_text(json.dumps(fixture), encoding='utf-8')
                # Positive control: valid accessible sample data exists. The
                # normal-mode gateway must not silently consume that data.
                control = JsonObservations(poison).read(db, range_minutes=1440)
                assert control.device(91002).metrics[0].cpu == 97.375
                lab_config.LOCAL_LAB = False; lab_config.FIXTURE_DIR = poison
                os.environ['COGNISHIELD_AI_LIVE_READS'] = '0'
                for surface in ['floating', 'studio']:
                    cid = (await call('POST', '/api/v1/ai/conversations', {'assistant_kind': surface}))['id']
                    await ask(cid, 'G9-NORMAL-NO-SIMULATION-' + surface,
                        'Read the available CPU telemetry for G9-Edge. If measurements are unavailable, say so.',
                        ['network.telemetry'], lambda value: '97.375' not in value['answer']
                        and not value['evidence'] and all(item['status'] == 'unavailable' for item in value['observations'])
                        and any(word in value['answer'].lower() for word in ['unavailable', 'disabled']))
            else:
                raw = ('hostname G9-UPLOAD\nrouter ospf 88\n router-id 198.51.100.88\n'
                       'router bgp 65088\n neighbor 192.0.2.89 remote-as 65189\n! UNTRUSTED_UPLOAD_CONFIG\n').encode()
                (run.path / 'uploaded-config.cfg').write_bytes(raw)
                for surface in ['floating', 'studio']:
                    cid = (await call('POST', '/api/v1/ai/conversations', {'assistant_kind': surface}))['id']
                    response = await client.post('/api/v1/ai/conversations/' + cid + '/attachments', content=raw,
                                                headers={'X-File-Name': 'g9-uploaded-config.cfg'})
                    response.raise_for_status(); attachment = response.json()['id']
                    await ask(cid, 'G9-UPLOADED-CONFIG-' + surface,
                        'What hostname, routing processes and BGP neighbor are written in g9-uploaded-config.cfg? Explain the saved file content, not current device state.',
                        ['document.read'], lambda value: all(word in value['answer'] for word in
                            ['G9-UPLOAD', '88', '65088', '192.0.2.89', '65189']), [attachment])
                    await ask(cid, 'G9-UPLOADED-NO-EXECUTION-' + surface,
                        'Does that file establish that any commands were executed?', ['document.read'],
                        lambda value: any(word in value['answer'].lower() for word in ['not', 'no ', 'cannot']))
    finally:
        db.close()
    (run.path / 'result.json').write_text(json.dumps({'source_context_assertions_pass': bool(outcomes) and all(outcomes),
        'executions': len(outcomes), 'passed': sum(outcomes), 'complete_answer_adequacy': 'PENDING_INDEPENDENT_FULL_REVIEW',
        'not_fresh_holdout': True}, indent=2), encoding='utf-8')
    return bool(outcomes) and all(outcomes)


if __name__ == '__main__':
    if sys.argv[1:] == ['--render-scan']:
        render_scan(); raise SystemExit(0)
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', required=True)
    parser.add_argument('--phase', choices=['seed', 'resume', 'scanned', 'normal', 'config'], required=True)
    raise SystemExit(0 if asyncio.run(main(parser.parse_args())) else 1)

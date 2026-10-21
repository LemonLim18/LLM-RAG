"""Shared Phase D evidence archive; no application/database writes or model downloads.

Run snapshot before a stage. Evaluators reuse Run.record, so failures and reruns
are separate immutable records rather than overwritten success reports.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
MODES = {'unit_deterministic', 'mocked_model_boundary', 'real_model_direct',
         'real_model_with_evidence', 'real_model_full_agent', 'real_browser'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def source_manifest():
    paths = []
    for folder, suffixes in [('backend', {'.py', '.json', '.j2', '.txt'}),
                             ('frontend', {'.tsx', '.ts', '.css', '.cjs', '.json'}),
                             ('docs/evaluations', {'.json', '.md'})]:
        for current, dirs, files in os.walk(ROOT / folder):
            dirs[:] = [d for d in dirs if d not in {'node_modules', 'dist', '__pycache__',
                                                   'knowledge_workspace', '.venv-m0', '.venv', 'db'}]
            paths.extend(Path(current) / name for name in files if Path(name).suffix in suffixes)
    return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sorted(paths)}


def database_fingerprints(path):
    """Only hashes/counts leave the read-only connection; no private rows logged."""
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as connection:
        tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        results = {}
        for name in tables:
            safe = name.replace('"', '""')
            rows = [json.dumps(list(r), default=lambda v: {'bytes_sha256': digest(v)},
                               sort_keys=True, separators=(',', ':'))
                    for r in connection.execute('SELECT * FROM "' + safe + '"')]
            results[name] = {'rows': len(rows), 'sha256': digest('\n'.join(sorted(rows)).encode())}
        return {'path': str(path), 'integrity': connection.execute('PRAGMA integrity_check').fetchone()[0],
                'foreign_key_errors': len(connection.execute('PRAGMA foreign_key_check').fetchall()), 'tables': results}


def snapshot():
    from lab_config import DB_PATH, MODE, LOCAL_OLLAMA_URL, LOCAL_OLLAMA_MODEL
    source = source_manifest()
    staged = git('diff', '--cached', '--binary', '--', '.')
    previous = ROOT / 'tmp/phase-c/baseline-index.json'
    expected = json.loads(previous.read_text())['patch_hash'] if previous.exists() else None
    if expected and digest(staged) != expected:
        raise RuntimeError('Protected staged checkpoint changed; inspect before Phase D mutation')
    pointer_path = ROOT / 'backend/knowledge_workspace/storage/catalog_releases/active.json'
    pointer = json.loads(pointer_path.read_text())
    release = pointer_path.parent / pointer['release_id']
    manifest = json.loads((release / 'manifest.json').read_text())
    if digest((release / 'manifest.json').read_bytes()) != pointer['manifest_sha256']:
        raise RuntimeError('Active knowledge manifest mismatch')
    for name, expected_hash in manifest['artifacts'].items():
        path = (release / name).resolve()
        if not path.is_relative_to(release.resolve()) or digest(path.read_bytes()) != expected_hash:
            raise RuntimeError('Active knowledge artifact mismatch: ' + name)
    return {'timestamp': datetime.now(timezone.utc).isoformat(),
            'head': git('rev-parse', 'HEAD').decode().strip(),
            'branch': git('branch', '--show-current').decode().strip(),
            'status': git('status', '--porcelain=v1', '--', '.').decode(),
            'staged_patch_sha256': digest(staged), 'source_digest': digest(json.dumps(source, sort_keys=True).encode()),
            'source_manifest': source, 'database': database_fingerprints(DB_PATH),
            'knowledge_authoring':{p.name:database_fingerprints(p) for p in sorted((ROOT/'backend/knowledge_workspace/storage/knowledge').glob('*.sqlite3'))},
            'knowledge': {**pointer, 'operations': len(manifest['schemas']), 'bindings': len(manifest['template_bindings']),
                          'retrieval': manifest['retrieval']},
            'runtime': {'mode': MODE, 'ollama_url': LOCAL_OLLAMA_URL, 'configured_model': LOCAL_OLLAMA_MODEL,
                        'frontend_port': 5173, 'backend_port': 8000}}


class Run:
    def __init__(self, stage, mode, manifest=None, *, phase='phase-d'):
        if mode not in MODES:
            raise ValueError('Unknown evaluation mode')
        self.mode = mode
        if phase not in {'phase-d','phase-e','phase-f','phase-g'}:raise ValueError('Unknown audit namespace')
        parent = ROOT / 'tmp' / phase
        if phase in {'phase-f','phase-g'}:parent = parent / 'iterations'
        self.path = parent / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + stage + '-' + uuid4().hex[:6])
        self.path.mkdir(parents=True, exist_ok=False)
        self.sequence = 0
        self.manifest = manifest or {'timestamp': datetime.now(timezone.utc).isoformat(), 'head': git('rev-parse', 'HEAD').decode().strip()}
        (self.path / 'manifest.json').write_text(json.dumps(self.manifest, indent=2), encoding='utf-8')

    def record(self, case, outcome, *, expected, actual, classification=None, **metadata):
        if outcome not in {'PASS', 'FAIL', 'BLOCKED', 'NOT RUN'}:
            raise ValueError('Unknown evaluation outcome')
        self.sequence += 1
        row = {'sequence': self.sequence, 'test_id': case, 'timestamp': datetime.now(timezone.utc).isoformat(),
               'evaluation_mode': self.mode, 'outcome': outcome, 'expected': expected, 'actual': actual,
               'failure_classification': classification, **metadata}
        # Exclusive create prevents accidentally erasing an original failed run.
        with (self.path / (f'{self.sequence:04d}-case.json')).open('x', encoding='utf-8') as stream:
            json.dump(row, stream, indent=2, default=str)
        with (self.path / 'cases.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, default=str) + '\n')
        return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['snapshot'])
    parser.add_argument('--stage', default='D0')
    args = parser.parse_args()
    started = time.monotonic()
    data = snapshot()
    run = Run(args.stage, 'unit_deterministic', data)
    run.record('D-SEC-BASELINE', 'PASS', expected='Protected index, verified knowledge and read-only ordinary data fingerprints',
               actual={k: v for k, v in data.items() if k not in {'source_manifest', 'status', 'database'}},
               latency_ms=round((time.monotonic() - started) * 1000, 2))
    print(json.dumps({'run': str(run.path), 'source_digest': data['source_digest'], 'staged': data['staged_patch_sha256'],
                      'knowledge': data['knowledge'], 'sqlite_integrity': data['database']['integrity']}))

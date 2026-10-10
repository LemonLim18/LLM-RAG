"""Explicit opt-in real configured model smoke, isolated documents; no ingestion."""
from unittest.mock import patch
from tests.test_workbench_edits import EditTests, TEXT

case = EditTests('test_real_catalog_rendered_proposal_without_any_writes')
try:
    case.setUp()
    with patch('app.document_edits.interpret', case._original_interpret):
        first = case.propose(instruction='Rename VLAN 20 from STAFF to ENGINEERING')
        print('REAL MODEL FIRST:', first.status_code, first.text, flush=True)
        assert first.status_code == 200 and first.json()['outcome'] == 'proposal', first.text
        proposed = first.json()['proposed_content']
        assert proposed == TEXT.replace('STAFF', 'ENGINEERING')
        second = case.propose(current_content=proposed, instruction='Rename VLAN 20 from ENGINEERING to FINANCE')
        print('REAL MODEL SECOND:', second.status_code, second.text, flush=True)
        assert second.status_code == 200 and second.json()['proposed_content'] == TEXT.replace('STAFF', 'FINANCE'), second.text
        assert case.client.get('/api/v1/workbench/working-documents/' + case.doc['document_id']).json()['content'] == TEXT
        print('PASS: actual configured inference, exact catalog/schema/device policy/Jinja rendering, two unsaved-base proposals; no persistence. Chroma/embeddings not used.', flush=True)
finally:
    case.doCleanups()

"""Read-only reconciliation. Writes reports only; never opens a knowledge SQLite DB."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from llm.gateway_knowledge import read_release, release_assessment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ordinary', type=Path, default=ROOT/'backend/knowledge_workspace/storage/catalog_releases')
    parser.add_argument('--isolated', type=Path, default=ROOT/'tmp/m4/k/storage/catalog_releases')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/shared_ai_coverage')
    args = parser.parse_args()
    assessments = {}
    catalogs = {}
    for label, root in [('ordinary', args.ordinary), ('isolated_test_only', args.isolated)]:
        release, _, _ = read_release(root)
        assessments[label] = release_assessment(root)
        catalogs[label] = {row['operation_id']: row for row in json.loads((release/'catalog/operations.json').read_text())}
    ordinary, isolated = catalogs.values()
    changes = {key: {'ordinary':ordinary.get(key), 'isolated_test_only':isolated.get(key)}
               for key in sorted(ordinary.keys() | isolated.keys()) if ordinary.get(key) != isolated.get(key)}
    rows = []
    for label, assessment in assessments.items():
        for row in assessment['coverage']:
            rows.append({'environment':label, 'release_id':assessment['release_id'], **row,
                'operation_aware_edit':'cisco_iosxe_rename_vlan_only' if row['operation_id']=='rename_vlan' and row['vendor']=='cisco' else 'unsupported',
                'runtime_acceptance':'not_individually_tested'})
        for operation in sorted(isolated.keys() - ordinary.keys()) if label == 'ordinary' else []:
            for vendor, platform in [('cisco','iosxe'), ('huawei','vrp'), ('juniper','junos')]:
                rows.append({'environment':label, 'release_id':assessment['release_id'], 'operation_id':operation,
                    'vendor':vendor, 'platform':platform, 'versions':[], 'native_status':'unsupported',
                    'native_reason':'Operation is isolated test knowledge only', 'playbook_status':'unsupported',
                    'operation_aware_edit':'unsupported','runtime_acceptance':'not_deployed'})
    report = {'authority':'Each workspace active pointer is authoritative only in that workspace.',
        'retention':'Preserve both unchanged. Never promote isolated lab_label fixtures. Selective adoption requires separately authorized authoring and publication.',
        'assessments':assessments, 'operation_contract_changes':changes, 'coverage':rows,
        'device_execution':False, 'index_operability':'not_checked'}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'assessment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    fields = ['environment','release_id','operation_id','vendor','platform','versions','native_status','native_reason',
              'playbook_status','operation_aware_edit','runtime_acceptance']
    with (args.output/'coverage.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fields,extrasaction='ignore');writer.writeheader()
        for row in rows: writer.writerow({**row,'versions':json.dumps(row['versions'])})
    print(json.dumps({'operations_assessed':len(ordinary.keys()|isolated.keys()),'rows':len(rows),
        'ordinary_operations':len(ordinary),'isolated_operations':len(isolated),'output':str(args.output)}))


if __name__ == '__main__': main()

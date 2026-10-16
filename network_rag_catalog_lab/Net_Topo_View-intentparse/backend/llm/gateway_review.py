"""Published catalog choices and explicit, revision-checked engineering selections."""
import json
from local_providers.knowledge import knowledge_root
from llm.gateway_knowledge import read_release


def catalog():
    root, manifest, pointer=read_release(knowledge_root()/'storage/catalog_releases')
    operations=json.loads((root/'catalog/operations.json').read_text(encoding='utf-8'))
    categories=json.loads((root/'catalog/categories.json').read_text(encoding='utf-8'))
    from llm.gateway_reference_drafts import reference_templates
    return {'derived_variables':sorted({key for b in manifest['template_bindings'] for key in b['input_contract'].get('derived',{})}), 'reference_templates':reference_templates(), 'release_id':pointer['release_id'],'categories':categories,
        'operations':[{'operation_id':op['operation_id'],'category_id':op['category_id'],
            'label':op['display_name'],'description':op.get('description',''),
            'schema':json.loads((root/manifest['schemas'][op['operation_id']]).read_text(encoding='utf-8'))} for op in operations],
        'templates':[{'id':binding['artifact_path'],'operation_id':binding['operation_id'],
            'vendor':binding['vendor'],'platform':binding['platform'],'versions':binding['versions'],
            'path':binding['template_path'],'status':'published'} for binding in manifest['template_bindings']]}

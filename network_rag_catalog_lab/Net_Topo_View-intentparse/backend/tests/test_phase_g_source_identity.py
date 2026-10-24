"""Source identities must outrank incidental document-topic similarity."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_documents import file_context_requested


LIBRARY=[{'name':'Design.md','category':'documents'},{'name':'Saved CLI.txt','category':'attachments'}]


def test_configuration_record_topics_do_not_identify_ambient_documents():
    for question in ['Read the most recent saved configuration capture for Alder.',
        'Explain the config_snapshots source for Alder.',
        'Read the config_drift source and its comparison time.']:
        assert not file_context_requested(question,LIBRARY)


def test_generic_demonstrative_without_file_antecedent_does_not_bind_library():
    assert not file_context_requested('Describe this interface state.',LIBRARY)
    assert not file_context_requested('Explain that route.',LIBRARY)


def test_actual_named_uploaded_and_prior_file_references_remain_bound():
    assert file_context_requested('Read Design.md.',LIBRARY)
    assert file_context_requested('Explain the uploaded configuration.',LIBRARY)
    assert file_context_requested('Can you read this, the content inside?',[{'name':'note.pdf','id':'owned-attachment'}])
    prior={'context_coverage':{'routing':{'attachments':True}}}
    assert file_context_requested('What about another page?',LIBRARY,prior)

"""Benchmark setup failures must be rejected before inference, not scored as AI errors."""
import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_phase_f_registry import validate_registry


def registry(surface='studio'):
    return {'routing_cases':[{'id':'TEST-SETUP','assistant':surface,'prompt':'Explain a generic concept.',
        'required_tools':[],'starting_state':{'setup_turns':[],'editor_fixture':'open','attachment_fixture':None}}],
        'editor_fixtures':{'open':'# Unrelated unsaved text\n'}}


def test_floating_editor_snapshot_is_an_invalid_benchmark_setup():
    with pytest.raises(ValueError,match='Floating.*editor'):validate_registry(registry('floating'))


def test_actual_studio_editor_setup_is_permitted():
    validate_registry(registry())


@pytest.mark.parametrize('field',['editor_fixture','attachment_fixture'])
def test_unknown_context_fixture_is_rejected_before_any_model_call(field):
    value=registry();value['routing_cases'][0]['starting_state'][field]='not-defined'
    with pytest.raises(ValueError,match='fixture'):validate_registry(value)


@pytest.mark.parametrize('contradictory',[False,True])
def test_declared_oracle_values_are_checked_against_the_actual_frozen_fixture(contradictory):
    value=json.loads((Path(__file__).resolve().parents[2]/'docs/evaluations/phase_g_lossless_quality_replacements_v1.json').read_text(encoding='utf-8'))
    if contradictory:
        value['quality_cases'][0]['fixture_assertions'][0]['expected']=65020
        with pytest.raises(ValueError,match='contradicts'):validate_registry(value)
    else:
        validate_registry(value)

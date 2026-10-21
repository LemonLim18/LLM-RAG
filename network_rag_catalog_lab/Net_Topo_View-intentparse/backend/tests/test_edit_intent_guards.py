"""Reviewable patches must satisfy bounded explicit edit constraints."""
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_documents import validate_edit_intent
from llm.gateway_models import EditorSnapshot

BASE='router ospf 7\n router-id 192.0.2.7\nrouter bgp 65007\n neighbor 192.0.2.8 remote-as 65008\n! PRESERVE_THIS_NOTE\n'


def body(prompt,content=BASE,**extra):
    return SimpleNamespace(prompt=prompt,editor=EditorSnapshot(document_id='test',path='playbooks/test.cfg',content=content,
        language='plaintext',model_id='monaco-test',model_version=1,buffer_epoch=1,saved_revision=0,is_dirty=True,read_only=False,**extra))


def test_comment_only_insertion_requires_comment_syntax_and_requested_location():
    request=body('Add a short explanation comment above BGP in the active file.')
    with pytest.raises(HTTPException):validate_edit_intent(request,BASE+'Explanation: Frozen routing configuration.\n')
    with pytest.raises(HTTPException):validate_edit_intent(request,BASE+'! BGP neighbor configuration.\n')
    with pytest.raises(HTTPException):validate_edit_intent(request,BASE.replace('router bgp 65007','!\nrouter bgp 65007\n'))
    correct=BASE.replace('router bgp 65007','! BGP neighbor configuration.\nrouter bgp 65007')
    validate_edit_intent(request,correct)
    with pytest.raises(HTTPException):validate_edit_intent(request,correct.replace('router ospf 7','router ospf 8'))


def test_only_indentation_preserves_all_nonindent_text_and_line_endings():
    request=body('Correct only the indentation in this open file.')
    validate_edit_intent(request,BASE.replace(' neighbor','  neighbor'))
    with pytest.raises(HTTPException):validate_edit_intent(request,BASE.replace('\n','\n\n'))
    with pytest.raises(HTTPException):validate_edit_intent(request,BASE.replace('65008','65009'))


def test_selected_edit_cannot_change_text_outside_the_supplied_region():
    text='def total(values):\n    result = sum(values)\n    return result\n'
    request=body('Modify only the selected Python block.',text,selection={'text':'    result = sum(values)','start_line':2,'end_line':2})
    validate_edit_intent(request,text.replace('    result =','    subtotal ='))
    with pytest.raises(HTTPException):validate_edit_intent(request,text.replace('def total','def result'))


def test_model_comment_cannot_call_the_local_as_a_bgp_id():
    import json
    from llm.gateway_documents import model_edit_patch,native_comment_insertion_context
    request=body('Add a short explanation comment above BGP in the active file.')
    context=native_comment_insertion_context(request)
    with pytest.raises(HTTPException):model_edit_patch(json.dumps({'comment':'Configure BGP neighbor with remote AS 65008 on router with BGP ID 65007'}),context,request.editor.path)
    patch=model_edit_patch(json.dumps({'comment':'BGP local AS 65007 peers with 192.0.2.8 in remote AS 65008.'}),context,request.editor.path)
    assert patch.replacements[0].old_text=='router bgp 65007'

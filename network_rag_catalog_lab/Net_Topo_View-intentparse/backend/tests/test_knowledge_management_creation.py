"""Focused category -> parameter -> operation -> template creation contract."""
from test_knowledge_authoring import app, TestClient, create_access_token


def test_creation():
    with TestClient(app) as client:
        client.headers['Authorization']='Bearer '+create_access_token(1,'creation-admin','admin')
        def call(method,path,body=None,status=200):
            r=client.request(method,'/api/v1/knowledge'+path,json=body)
            assert r.status_code==status,(r.status_code,r.text[:2500])
            return r.json()
        call('POST','/initialize',{'reason':'Creation workflow test'})
        def edit(changes):
            return call('POST','/edit',{'expected_revision':call('GET','')['revision'],'reason':'Authoring test','changes':changes})
        edit([{'entity':'category','action':'create','entity_id':'lab_category','values':{'display_name':'Lab category','aliases':[],'description':'Test category'}},
              {'entity':'parameter','action':'create','entity_id':'lab_number','values':{'display_name':'Lab number','aliases':[],'value_type':'integer'}},
              {'entity':'membership','action':'assign','values':{'category_id':'lab_category','parameter_id':'lab_number'}},
              {'entity':'operation','action':'create','entity_id':'lab_operation','values':{'display_name':'Lab operation','category_id':'lab_category','aliases':[]}}])
        edit([{'entity':'contract','action':'replace','entity_id':'lab_operation','values':{'version':2,'mappings':[
            {'operation_id':'lab_operation','operation_version':2,'category_id':'lab_category','parameter_id':'lab_number','field_path':'lab_number','position':0,'required':True,'required_order':0}],
            'rules':[{'operation_id':'lab_operation','operation_version':2,'field_path':'','keywords':{'type':'object','additionalProperties':False}},
                     {'operation_id':'lab_operation','operation_version':2,'field_path':'lab_number','keywords':{'minimum':1,'maximum':100}}], 'templates':[]}}])
        schema=call('GET','/schema/lab_operation')['data']['schema']
        assert schema['properties']['lab_number']['maximum']==100 and schema['required']==['lab_number']
        variant={'expected_revision':call('GET','')['revision'],'reason':'Add reviewed variant','path':'','content':'lab {{ lab_number }}',
                 'operation_id':'lab_operation','vendor':'cisco','platform':'iosxe','versions':['17.9']}
        call('PUT','/template',variant)
        state=call('GET','')
        binding=next(r for r in state['data']['catalogs']['template_bindings'] if r['operation_id']=='lab_operation')
        assert state['data']['templates'][binding['template_path']]=='lab {{ lab_number }}'
        call('PUT','/template',{**variant,'expected_revision':state['revision']},422)
        edit([{'entity':'operation','action':'update','entity_id':'lab_operation','values':{'status':'active'}}])
        call('POST','/validate')
        print('PASS: category, global parameter, pool, operation, required/range compilation, SQLite template variant, overlap rejection and activation',flush=True)


if __name__=='__main__':test_creation()

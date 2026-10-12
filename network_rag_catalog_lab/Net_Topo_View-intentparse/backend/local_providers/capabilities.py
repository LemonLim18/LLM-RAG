"""Capabilities describe implemented actions, independently of page availability."""
def local_capabilities():
    return {
        'mode':'local_lab','storage':'sqlite','remote_execution':False,'remote_sync':False,
        'scheduled_jobs':[], 'telemetry':'editable_json','topology':'stored_inventory',
        'ai_available':True,
        'providers':{'inventory':'sqlite','observations':'json_fixture','authoring':'sqlite_revisions','chat':'local_ollama'},
        'features':{
            'inventory.write':True,'profiles.write':True,'templates.write':True,
            'studio.authoring':True,'observations.read':True,'template_git.status':False,
            'template_git.remote':False,'onboarding.register_ui':True,
            'onboarding.ztp_simulation':True,'approval.workflow_ui':True,
            'backup.restore_simulation_ui':True,'policy.evaluate_stored_ui':True,'execution.ssh':False,
            'execution.deploy':False,'ai.generate':True,'ai.local_chat':True
        },
        'unavailable':['netbox_sync','crawler','ssh','ansible_execution','sdn_commands','live_telemetry']
    }


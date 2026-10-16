"""WSL is a runtime, not a sandbox. No verified containment means unavailable."""
import json
import os
from pathlib import Path
import subprocess


def validate_ansible(content, required_plugins=None):
    unavailable = {'status':'unavailable','syntax':'not_run','lint':'not_run',
        'platform_compatibility':'not_established','semantic_validation':'not_established',
        'device_testing':'not_run','deployment_authorized':False}
    profile = os.getenv('COGNISHIELD_WSL_VALIDATION_PROFILE')
    if not profile or not profile.startswith('/opt/cognishield-validator/') or '..' in profile.split('/'):
        return {**unavailable,'message':'Configure an approved pinned WSL validation profile; no unsafe fallback is used'}
    command=['wsl.exe','--distribution',os.getenv('COGNISHIELD_WSL_DISTRO','Ubuntu-22.04'),
        '--exec','python3','-I','-c',Path(__file__).with_name('wsl_validation_worker.py').read_text(encoding='utf-8')]
    try:
        result=subprocess.run(command,input=json.dumps({'profile':profile,'content':content,'required_plugins':required_plugins or {}}),
            capture_output=True,text=True,encoding='utf-8',timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if len(result.stdout)>200000 or len(result.stderr)>100000:
            return {**unavailable,'message':'Validation output limit exceeded'}
        output=json.loads(result.stdout)
        if output.get('containment_verified') is not True:
            return {**unavailable,'message':output.get('message','Containment was not verified')}
        return {**unavailable,**output}
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return {**unavailable,'message':'WSL validation unavailable or timed out; no device action was attempted'}

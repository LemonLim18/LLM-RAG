"""Trusted Linux launcher: bind only pinned tools and staged inputs into bwrap."""
import hashlib
import json
import os
import re
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile


def run(payload):
    if os.getuid()==0:
        raise ValueError('Validation must run as an unprivileged WSL user')
    if not shutil.which('bwrap'):
        raise ValueError('bubblewrap is unavailable; WSL alone is not a sandbox')
    profile=Path(payload['profile']).resolve()
    if not profile.is_relative_to('/opt/cognishield-validator') or profile.is_symlink():
        raise ValueError('Unapproved validation profile')
    manifest=json.loads((profile/'profile.json').read_text())
    if not manifest.get('dependencies') or not manifest.get('files'):
        raise ValueError('Validation profile must declare pinned dependencies and file hashes')
    for name,expected in manifest['files'].items():
        file=(profile/name).resolve()
        if not file.is_relative_to(profile) or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
            raise ValueError('Validation profile integrity failed')
    for file in profile.rglob('*'):
        if file.is_file() and file.relative_to(profile).as_posix() != 'profile.json' and file.relative_to(profile).as_posix() not in manifest['files']:
            raise ValueError('Validation profile contains unregistered files')
    for collection,version in manifest['dependencies'].items():
        if not re.fullmatch(r'[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*',collection):
            raise ValueError('Invalid pinned collection name')
        namespace,name=collection.split('.')
        installed=json.loads((profile/'collections/ansible_collections'/namespace/name/'MANIFEST.json').read_text())
        if installed['collection_info']['version'] != version:
            raise ValueError('Installed collection version differs from the pinned profile')
    for executable in ['bin/python','bin/ansible-playbook','bin/ansible-lint','bin/ansible-doc']:
        if executable not in manifest['files']:
            raise ValueError('Validation executable is not integrity pinned')
    # Limits also cover bubblewrap, probes and any child processes.
    resource.setrlimit(resource.RLIMIT_AS,(1024*1024*1024,1024*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(45,45))
    resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024*1024,2*1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    resource.setrlimit(resource.RLIMIT_NPROC,(32,32))
    with tempfile.TemporaryDirectory(prefix='cognishield-validate-') as folder:
        work=Path(folder)
        (work/'playbook.yml').write_text(payload['content'],encoding='utf-8')
        (work/'inventory.yml').write_text('all:\n  hosts:\n    validation_target:\n      ansible_connection: local\n',encoding='utf-8')
        (work/'ansible.cfg').write_text('[defaults]\ninventory=/work/inventory.yml\nretry_files_enabled=False\ncollections_path=/tools/collections\nlocal_tmp=/tmp/ansible\n',encoding='utf-8')
        (work/'.ansible-lint').write_text('offline: true\n',encoding='utf-8')
        base=['bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv',
            '--ro-bind','/usr','/usr','--ro-bind',str(profile),str(profile),'--ro-bind',str(profile),'/tools','--ro-bind',str(work),'/work',
            '--tmpfs','/tmp','--dir','/home','--proc','/proc','--dev','/dev','--chdir','/work',
            '--setenv','HOME','/tmp','--setenv','PATH','/tools/bin:/usr/bin',
            '--setenv','ANSIBLE_CONFIG','/work/ansible.cfg','--setenv','ANSIBLE_HOME','/tmp/ansible-home',
            '--setenv','ANSIBLE_COLLECTIONS_PATH','/tools/collections','--setenv','ANSIBLE_NOCOLOR','1']
        for library in ['/lib','/lib64']:
            if Path(library).exists(): base+=['--ro-bind',library,library]
        # Prove host mounts, inherited secrets and routable networking are absent.
        probe='''import os,socket
assert not os.path.exists('/mnt/c') and not os.path.exists('/run')
assert not os.path.exists('/root')
assert set(os.listdir('/home')) == set()
assert not any(k.endswith(('TOKEN','PASSWORD','SECRET','KEY')) for k in os.environ)
s=socket.socket();s.settimeout(.2)
try:
 s.connect(('192.0.2.1',9))
 raise AssertionError('network unexpectedly available')
except OSError: pass
'''
        checked=subprocess.run(base+['/usr/bin/python3','-I','-c',probe],capture_output=True,timeout=5)
        if checked.returncode: raise ValueError('Containment self-test failed')
        for plugin_type,names in payload.get('required_plugins',{}).items():
            if plugin_type not in {'module','connection','cliconf','netconf'}:
                raise ValueError('Invalid required plugin type')
            for name in names:
                if not re.fullmatch(r'[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}',name):
                    raise ValueError('Required plugins must be fully qualified')
                doc=subprocess.run(base+['/tools/bin/ansible-doc','-j','-t',plugin_type,name],capture_output=True,text=True,timeout=5)
                if doc.returncode or name not in json.loads(doc.stdout):
                    raise ValueError('Required plugin is unavailable: '+name)
        reports={}
        for name,args in [('syntax',['/tools/bin/ansible-playbook','--syntax-check','/work/playbook.yml']),
                          ('lint',['/tools/bin/ansible-lint','--offline','-c','/work/.ansible-lint','/work/playbook.yml'])]:
            result=subprocess.run(base+args,capture_output=True,text=True,timeout=20)
            reports[name]='passed' if result.returncode==0 else 'failed'
            reports[name+'_output']=(result.stdout+result.stderr)[:40000]
        return {'status':'passed' if all(reports[k]=='passed' for k in ['syntax','lint']) else 'failed',
            'containment_verified':True,**reports,'dependencies':manifest['dependencies']}


try:
    print(json.dumps(run(json.load(__import__('sys').stdin))))
except Exception as exc:
    print(json.dumps({'status':'unavailable','containment_verified':False,'message':str(exc)}))

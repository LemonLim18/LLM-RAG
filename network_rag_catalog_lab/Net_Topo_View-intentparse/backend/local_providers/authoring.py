"""SQLite revision overlay over existing authorized file roots; no disk writes."""
import json
import re
from pathlib import Path, PurePosixPath
from fastapi import HTTPException
from db.manager import DatabaseManager
from lab_config import DB_PATH, BACKEND_DIR

ROOTS={'templates':BACKEND_DIR/'templates','schemas':BACKEND_DIR/'config_engine'/'schemas','ansible':BACKEND_DIR/'ansible'}

class AuthoringStore:
    def __init__(self, db=None, roots=None):
        self.db=db or DatabaseManager(str(DB_PATH))
        self.roots=roots or ROOTS

    def resolve(self, namespace, value, write=False, kind='file'):
        if namespace not in self.roots or not isinstance(value,str) or len(value)>240:
            raise HTTPException(422,'Invalid authoring path')
        parts=PurePosixPath(value).parts
        if not parts or value.startswith('/') or '\\' in value or any(p in {'.','..'} or not re.fullmatch(r'[A-Za-z0-9_. -]+',p) or ':' in p for p in value.split('/')):
            raise HTTPException(422,'Authoring paths must be relative, normalized and inside the authorized root')
        root=self.roots[namespace].resolve()
        path=(root/value).resolve()
        if not path.is_relative_to(root) or any((root.joinpath(*parts[:i])).is_symlink() for i in range(1,len(parts)+1)):
            raise HTTPException(403,'Path escapes authorized authoring root')
        if namespace=='ansible':
            allowed={'playbooks','roles'} if write else {'playbooks','roles','reference','Test_Reference'}
            if parts[0] not in allowed or (write and len(parts)<2):
                raise HTTPException(403,'Only playbooks/ and roles/ are writable local workspace roots')
            if kind=='file' and path.suffix.lower() not in {'.yml','.yaml','.json','.j2','.md','.txt'}:
                # A generated text artifact may declare its own suffix in its
                # frozen template. Trust only the exact persisted job manifest,
                # not arbitrary filenames or client-supplied extensions.
                match = re.fullmatch(r'playbooks/generated/job_(\d+)/[^/]+', value)
                registered = False
                if match:
                    with self.db._connect() as conn:
                        row = conn.execute('SELECT ansible_artifact_manifest FROM jobs WHERE id=?', (int(match[1]),)).fetchone()
                    if row and row[0]:
                        manifest = json.loads(row[0])
                        registered = (manifest.get('engine') == 'v9'
                            and manifest.get('artifact_metadata', {}).get('extension') == path.suffix
                            and any(item.get('path') == value for item in manifest.get('files', [])))
                if not registered:
                    raise HTTPException(422,'Unsupported authoring file type')
        elif namespace=='templates':
            from config_engine.renderer import SUPPORTED_VENDORS
            if len(parts)!=2 or parts[0] not in SUPPORTED_VENDORS or path.suffix!='.j2':
                raise HTTPException(422,'Invalid template vendor or name')
        elif len(parts)!=1 or path.suffix!='.json':
            raise HTTPException(422,'Invalid schema filename')
        return path

    def latest(self,namespace,path,c=None):
        if c is not None:
            row=c.execute('SELECT * FROM authoring_revisions WHERE namespace=? AND path=? ORDER BY revision DESC LIMIT 1',(namespace,path)).fetchone()
            return dict(row) if row else None
        with self.db._connect() as conn:
            return self.latest(namespace,path,conn)

    def read(self,namespace,path):
        disk=self.resolve(namespace,path)
        row=self.latest(namespace,path)
        if row:
            if row['deleted'] or row['kind']!='file': raise FileNotFoundError(path)
            return row['content']
        if not disk.is_file(): raise FileNotFoundError(path)
        return disk.read_text(encoding='utf-8')

    def entries(self,namespace):
        root=self.roots[namespace]
        entries={}
        if root.exists():
            for path in root.rglob('*'):
                if not path.is_file(): continue
                rel=path.relative_to(root).as_posix()
                try: self.resolve(namespace,rel)
                except HTTPException: continue
                entries[rel]={'path':rel,'kind':'file','revision':0,'source':'stored'}
        with self.db._connect() as c:
            rows=c.execute('SELECT r.* FROM authoring_revisions r JOIN (SELECT path,MAX(revision) revision FROM authoring_revisions WHERE namespace=? GROUP BY path) latest ON r.path=latest.path AND r.revision=latest.revision WHERE r.namespace=?',(namespace,namespace)).fetchall()
        for r in rows:
            if r['deleted']: entries.pop(r['path'],None)
            else: entries[r['path']]={'path':r['path'],'kind':r['kind'],'revision':r['revision'],'source':'stored'}
        return entries

    def validate_content(self,namespace,path,content):
        if len(content.encode('utf-8'))>2000000: raise HTTPException(422,'Authoring content exceeds 2 MB')
        try:
            if namespace=='templates':
                from jinja2.sandbox import SandboxedEnvironment
                SandboxedEnvironment().parse(content)
            elif namespace=='schemas':
                from jsonschema import Draft202012Validator
                schema=json.loads(content)
                # Validation must never retrieve a remote reference.
                def check(node):
                    if isinstance(node,dict):
                        if '$ref' in node and not str(node['$ref']).startswith('#'): raise ValueError('Only local JSON schema references are supported')
                        for v in node.values(): check(v)
                    elif isinstance(node,list):
                        for v in node: check(v)
                check(schema); Draft202012Validator.check_schema(schema)
        except Exception as exc:
            raise HTTPException(422,'Invalid source: '+str(exc)) from exc

    def mutate(self,namespace,path,content,actor,operation='save',kind='file'):
        disk=self.resolve(namespace,path,write=True,kind=kind)
        if operation!='delete' and kind=='file': self.validate_content(namespace,path,content)
        with self.db._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=self.latest(namespace,path,c)
            exists=(not row['deleted']) if row else disk.exists()
            if operation=='create' and exists: raise HTTPException(409,'Path already exists')
            if operation in {'save','delete'} and not exists: raise HTTPException(404,'Path not found')
            if (row and row['kind']=='dir') or disk.is_dir():
                if operation!='create': raise HTTPException(409,'Folder mutation is deferred; edit individual files')
            if row is None and disk.is_file():
                # Preserve original content as revision 1 before its first local edit.
                c.execute('INSERT INTO authoring_revisions(namespace,path,revision,content,actor) VALUES (?,?,1,?,?)',(namespace,path,disk.read_text(encoding='utf-8'),actor))
                revision=2
            else: revision=(row['revision']+1) if row else 1
            c.execute('INSERT INTO authoring_revisions(namespace,path,revision,content,kind,deleted,actor) VALUES (?,?,?,?,?,?,?)',
                (namespace,path,revision,content if operation!='delete' else None,kind,int(operation=='delete'),actor))
            c.execute('INSERT INTO audit_log(user_id,action,target,details) VALUES (?,?,?,?)',
                (actor,'authoring.'+operation,namespace+'/'+path,json.dumps({'revision':revision,'source':'stored'})))
        return {'path':path,'status':'deleted' if operation=='delete' else 'saved','source':'stored','revision':revision,'executed':False}

    def history(self,namespace,path):
        self.resolve(namespace,path)
        with self.db._connect() as c:
            return [dict(r) for r in c.execute('SELECT revision,content,deleted,kind,actor,created_at FROM authoring_revisions WHERE namespace=? AND path=? ORDER BY revision DESC',(namespace,path))]


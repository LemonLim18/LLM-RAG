"""Owner-bound, JSON-only investigation checkpoints in the conversation database.

Only the memory channel is durable. Recovery starts a fresh read-only graph turn,
not a replay of old tool outputs or pending writes. Authorization stays in closure.
"""
import json
from uuid import uuid4
from fastapi import HTTPException
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple
from pydantic import Field,field_validator
from llm.gateway_models import StrictModel

SCHEMA = 1


class InvestigationMemory(StrictModel):
    schema_version: int = SCHEMA
    goal: str = Field(default='',max_length=2000)
    device_refs: list[str] = Field(default_factory=list,max_length=8)
    interface_refs: list[str] = Field(default_factory=list,max_length=100)
    entities: list[dict] = Field(default_factory=list,max_length=100)
    domains: list[str] = Field(default_factory=list,max_length=8)
    source_requests: dict[str,dict] = Field(default_factory=dict,max_length=8)
    attributes: list[str] = Field(default_factory=list,max_length=10)
    documents: list[str] = Field(default_factory=list,max_length=5)
    evidence_revisions: dict[str,str] = Field(default_factory=dict,max_length=60)
    evidence_refs: list[str] = Field(default_factory=list,max_length=60)
    turn_ref: str = Field(default='',max_length=36)
    editor_ref: dict = Field(default_factory=dict)
    engineering_request_ref: str = Field(default='',max_length=36)
    engineering_kind: str = Field(default='',pattern='^(|edit_proposal|generation_preview)$')
    open_questions: list[str] = Field(default_factory=list,max_length=20)
    status: str = Field(default='running',pattern='^(running|awaiting_response|completed|interrupted|cancelled)$')

    @field_validator('source_requests')
    @classmethod
    def valid_scopes(cls,value):
        from llm.gateway_references import source_scope_references
        return source_scope_references(value)


class InvestigationSaver(BaseCheckpointSaver):
    """The installed LangGraph saver API, with bounded sanitized SQLite storage."""
    def __init__(self,store,auth,request_id):
        super().__init__();self.store=store;self.auth=auth;self.request_id=request_id
        store.get(auth.conversation_id,auth.principal,auth.assistant_kind)
        with store.db._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            # Opportunistic retention only affects orchestration metadata.
            c.execute("DELETE FROM ai_agent_checkpoints WHERE thread_id IN (SELECT id FROM ai_agent_investigations WHERE updated_at<datetime('now','-30 days'))")
            c.execute("DELETE FROM ai_agent_investigations WHERE updated_at<datetime('now','-30 days')")
            row=c.execute('SELECT * FROM ai_agent_investigations WHERE conversation_id=? AND owner=? AND assistant=?',
                (auth.conversation_id,auth.principal,auth.assistant_kind)).fetchone()
            self.thread=row['id'] if row else uuid4().hex
            if not row:
                c.execute('INSERT INTO ai_agent_investigations(id,conversation_id,owner,assistant,schema_version,request_id,status) VALUES (?,?,?,?,?,?,?)',
                    (self.thread,auth.conversation_id,auth.principal,auth.assistant_kind,SCHEMA,request_id,'running'))
            self.restored_status=row['status'] if row else None

    def _check(self,c,config=None,writing=False):
        self.store.get(self.auth.conversation_id,self.auth.principal,self.auth.assistant_kind,c)
        row=c.execute('SELECT * FROM ai_agent_investigations WHERE id=? AND conversation_id=? AND owner=? AND assistant=?',
            (self.thread,self.auth.conversation_id,self.auth.principal,self.auth.assistant_kind)).fetchone()
        if not row:raise HTTPException(404,'Investigation is no longer available')
        if config and config.get('configurable',{}).get('thread_id')!=self.thread:
            raise HTTPException(403,'Checkpoint is outside this conversation')
        if writing:
            turn=c.execute('SELECT state FROM ai_turns WHERE conversation_id=? AND request_id=?',
                (self.auth.conversation_id,self.request_id)).fetchone()
            if not turn or turn[0]!='running':raise HTTPException(409,'Investigation turn is no longer active')
        return row

    def load_memory(self):
        with self.store.db._connect() as c:
            row=self._check(c)
            if row['schema_version']!=SCHEMA:return InvestigationMemory(), 'schema_reset'
            saved=c.execute('SELECT body FROM ai_agent_checkpoints WHERE thread_id=? ORDER BY rowid DESC LIMIT 1',(self.thread,)).fetchone()
        if not saved:return InvestigationMemory(), 'empty'
        try:
            memory=InvestigationMemory.model_validate(json.loads(saved[0])['channel_values']['memory'])
            if memory.schema_version!=SCHEMA:return InvestigationMemory(), 'schema_reset'
            return memory, 'restored'
        except (ValueError,KeyError,TypeError):return InvestigationMemory(), 'invalid_reset'

    def config(self):
        # Namespace is generated by the server from an already-owned turn; no API
        # accepts checkpoint identities or exposes a general resume command.
        return {'configurable':{'thread_id':self.thread,'checkpoint_ns':self.request_id},'recursion_limit':35}

    def get_tuple(self,config):
        with self.store.db._connect() as c:
            self._check(c,config)
            cfg=config['configurable'];args=[self.thread,cfg.get('checkpoint_ns','')]
            query='SELECT * FROM ai_agent_checkpoints WHERE thread_id=? AND namespace=?'
            if cfg.get('checkpoint_id'):query+=' AND checkpoint_id=?';args.append(cfg['checkpoint_id'])
            row=c.execute(query+' ORDER BY rowid DESC LIMIT 1',args).fetchone()
        if not row:return None
        result={'configurable':{'thread_id':self.thread,'checkpoint_ns':row['namespace'],'checkpoint_id':row['checkpoint_id']}}
        return CheckpointTuple(result,json.loads(row['body']),json.loads(row['metadata']),None,[])

    async def aget_tuple(self,config):return self.get_tuple(config)

    def put(self,config,checkpoint,metadata,new_versions):
        memory=InvestigationMemory.model_validate(checkpoint.get('channel_values',{}).get('memory',{}))
        # Deliberately exclude request/editor/results/evidence/raw context and
        # framework task writes. JSON only: no pickle or arbitrary type loading.
        safe={k:v for k,v in checkpoint.items() if k in {'v','id','ts','channel_versions','versions_seen','updated_channels'}}
        safe['channel_values']={'memory':memory.model_dump()}
        cfg=config['configurable'];namespace=cfg.get('checkpoint_ns','')
        with self.store.db._connect() as c:
            c.execute('BEGIN IMMEDIATE');self._check(c,config,True)
            c.execute('INSERT OR REPLACE INTO ai_agent_checkpoints(thread_id,namespace,checkpoint_id,body,metadata) VALUES (?,?,?,?,?)',
                (self.thread,namespace,checkpoint['id'],json.dumps(safe),json.dumps({k:v for k,v in metadata.items() if k in {'source','step'}})))
            c.execute("UPDATE ai_agent_investigations SET request_id=?,status=?,schema_version=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (self.request_id,memory.status,SCHEMA,self.thread))
            c.execute('DELETE FROM ai_agent_checkpoints WHERE thread_id=? AND rowid NOT IN (SELECT rowid FROM ai_agent_checkpoints WHERE thread_id=? ORDER BY rowid DESC LIMIT 32)',(self.thread,self.thread))
        return {'configurable':{**cfg,'checkpoint_id':checkpoint['id']}}

    async def aput(self,config,checkpoint,metadata,new_versions):return self.put(config,checkpoint,metadata,new_versions)
    def put_writes(self,config,writes,task_id,task_path=''):
        with self.store.db._connect() as c:self._check(c,config,True)
    async def aput_writes(self,config,writes,task_id,task_path=''):self.put_writes(config,writes,task_id,task_path)

    def mark(self,status):
        with self.store.db._connect() as c:
            self._check(c)
            c.execute('UPDATE ai_agent_investigations SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND request_id=?',(status,self.thread,self.request_id))

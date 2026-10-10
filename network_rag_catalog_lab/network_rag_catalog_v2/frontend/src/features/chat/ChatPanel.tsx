import { Bot, Sparkles, UserRound } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useWorkbench } from '../../app/workbenchContext';
import { ChatInput } from './ChatInput';
import { PlanningResult } from './PlanningResult';
import { SessionRecovery } from './SessionRecovery';
import { useDocumentEdit } from './useDocumentEdit';

export function ChatPanel() {
  const { state, dispatch, localPlanning } = useWorkbench();
  const [mode, setMode] = useState<'demo' | 'local_v9' | 'edit'>('demo');
  const local = mode !== 'demo';
  const editing = mode === 'edit';
  const edit = useDocumentEdit(editing);
  const planning = localPlanning.state;
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' });
  }, [state.chatMessages.length]);

  return (
    <aside className="panel chat-panel" aria-label="AI Copilot">
      <div className="panel-heading panel-heading--copilot">
        <div><span className="eyebrow">Integrated assistant</span><h2><Sparkles size={16} /> AI Copilot</h2></div>
        <span className="mock-badge">{local ? 'LOCAL V9' : 'MOCK'}</span>
      </div>
      <div className="chat-mode" aria-label="Copilot mode">
        <button type="button" aria-pressed={!local} onClick={() => setMode('demo')}>Demo mock</button>
        <button type="button" aria-pressed={mode === 'local_v9'} onClick={() => setMode('local_v9')}>Local V9</button>
        <button type="button" aria-pressed={editing} onClick={() => setMode('edit')}>Edit active file</button>
      </div>
      <div className="demo-callout">
        <Bot size={15} />
        {editing ? 'Local V9 document edit · review before accepting · Save separately. No device execution.' : local ? 'Real V9 planning · local models · synthetic inventory. Preview only; no device execution.' : 'Demo responses only. Messages never use the status API, V9, or a model.'}
      </div>
      <div className="chat-thread" aria-live="polite">
        {!local && state.chatMessages.map((message) => (
          <article key={message.id} className={`message message--${message.role}`}>
            <div className="message-avatar">{message.role === 'assistant' ? <Bot size={15} /> : <UserRound size={15} />}</div>
            <div className="message-body">
              <div className="message-meta"><strong>{message.role === 'assistant' ? 'Demo Copilot' : 'You'}</strong><span>{message.createdAt}</span></div>
              <p>{message.content}</p>
              {message.mock && <span className="message-provenance">LOCAL MOCK</span>}
            </div>
          </article>
        ))}
        {editing && <section aria-label="Local V9 document editing">
          <h3>Edit active working file</h3>
          {edit.tab && state.workspaceView === 'working' ? <><p>{edit.tab.saved.original.hostname} · {edit.tab.saved.original.operation_id}</p>
            <p className="planning-id">{edit.tab.saved.document_id}</p>
            <p>Current accepted buffer, including unsaved edits. Historical source; full document unvalidated.</p></> : <p>Open a Working File to request an edit. Samples, originals and previews are not editable through AI.</p>}
          <p>Supported now: one existing Cisco IOS XE VLAN name change with a reviewed V9 device profile and recorded VLAN facts (for example, SW1 / VLAN 20). Include the VLAN ID and new name.</p>
          {!edit.available && !edit.pending && <p>Keep the working editor active; finish any pending review or save conflict first.</p>}
          {edit.message && <p role={edit.error ? 'alert' : 'status'}>{edit.message}</p>}
          {edit.result && <details><summary>Last V9 edit interpretation</summary><p className="planning-id">Response for {edit.result.document_id}</p><p>{edit.result.operation_id} · {edit.result.outcome}</p>
            <pre>{JSON.stringify({ parameters: edit.result.parameters, evidence: edit.result.evidence, authority: edit.result.authority }, null, 2)}</pre>
            <p>Validation covers this bounded operation only, not the whole document or live device state.</p></details>}
        </section>}
        {local && !editing && <>
          <SessionRecovery />
          {planning.phase === 'idle' && <p className="empty-state">Submit a request to create a persisted V9 planning session.</p>}
          {planning.request && <article className="message message--user"><div className="message-body"><strong>You · Local V9 request</strong><p>{planning.request.prompt}</p><p className="planning-id">Request: {planning.request.client_request_id}</p></div></article>}
          {planning.phase === 'pending' && <p role="status">V9 is processing… No automatic retries. You can continue editing sample tabs.</p>}
          {planning.phase === 'error' && <div className="planning-error" role="alert">
            <p>{planning.error}</p>
            <p>Use Check creation outcome to inspect the durable receipt, including after a backend restart. No request is replayed. An incomplete receipt may remain indeterminate.</p>
            <p className="planning-id">Request: {planning.request?.client_request_id}</p>
            <button type="button" disabled={localPlanning.busy} onClick={localPlanning.reset}>New request (may create another session)</button>
          </div>}
          {planning.result && <PlanningResult result={planning.result} />}
        </>}
        <div ref={endRef} />
      </div>
      <ChatInput key={mode} local={local} editing={editing} disabled={editing ? !edit.available || edit.pending : local && (localPlanning.busy || planning.phase === 'error' || localPlanning.answerState.phase === 'error')}
        onSend={editing ? edit.submit : local ? localPlanning.submit : (message) => dispatch({ type: 'SEND_MOCK_MESSAGE', message })} />
      <p className="composer-note">Enter to send · Shift+Enter for a new line</p>
    </aside>
  );
}

import { Bot, Sparkles, UserRound } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useWorkbench } from '../../app/workbenchContext';
import { ChatInput } from './ChatInput';
import { PlanningResult } from './PlanningResult';
import { SessionRecovery } from './SessionRecovery';

export function ChatPanel() {
  const { state, dispatch, localPlanning } = useWorkbench();
  const [mode, setMode] = useState<'demo' | 'local_v9'>('demo');
  const local = mode === 'local_v9';
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
        <button type="button" aria-pressed={local} onClick={() => setMode('local_v9')}>Local V9</button>
      </div>
      <div className="demo-callout">
        <Bot size={15} />
        {local ? 'Real V9 planning · local models · synthetic inventory. Preview only; no device execution.' : 'Demo responses only. Messages never use the status API, V9, or a model.'}
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
        {local && <>
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
      <ChatInput key={mode} local={local} disabled={local && (localPlanning.busy || planning.phase === 'error' || localPlanning.answerState.phase === 'error')}
        onSend={local ? localPlanning.submit : (message) => dispatch({ type: 'SEND_MOCK_MESSAGE', message })} />
      <p className="composer-note">Enter to send · Shift+Enter for a new line</p>
    </aside>
  );
}

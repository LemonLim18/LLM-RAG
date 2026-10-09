import { AlertTriangle, CheckCircle2, CircleDashed, FileCode2, Network, Server } from 'lucide-react';
import { useWorkbench } from '../../app/workbenchContext';
import type { Json, PlanningTask } from '../../services/planningApi';

function textField(record: Record<string, Json>, field: string): string {
  const value = record[field];
  return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
}

function json(value: unknown): string {
  return JSON.stringify(value, null, 2) ?? String(value);
}

function statusLabel(status: string): string {
  return ({
    rendered: 'Rendered preview',
    validated: 'Validated',
    needs_clarification: 'Clarification required',
    needs_confirmation: 'Confirmation required',
    failed: 'Failed',
    collecting: 'Collecting',
  } as Record<string, string>)[status] ?? status.replaceAll('_', ' ');
}

function StatusBadge({ status }: { status: string }) {
  const safeStatus = ['ready', 'rendered', 'validated'].includes(status) ? 'ready'
    : status === 'failed' ? 'failed'
      : ['needs_clarification', 'needs_confirmation'].includes(status) ? 'pending' : 'neutral';
  return <span className={`task-status task-status--${safeStatus}`} data-v9-status={status}>{statusLabel(status)}</span>;
}

function IssueList({ title, issues }: { title: string; issues: Array<Record<string, Json>> }) {
  if (!issues.length) return null;
  return (
    <section className="review-section" aria-label={title}>
      <h4><AlertTriangle size={14} />{title} <span>{issues.length}</span></h4>
      <div className="issue-list">
        {issues.map((issue, index) => (
          <article className="issue-card" key={`${textField(issue, 'type')}:${textField(issue, 'field')}:${index}`}>
            <strong>{textField(issue, 'type') || 'V9 issue'}</strong>
            {textField(issue, 'field') && <code>{textField(issue, 'field')}</code>}
            <p>{textField(issue, 'message') || json(issue)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function TaskListItem({ task, selected, onSelect }: { task: PlanningTask; selected: boolean; onSelect: () => void }) {
  const intentId = task.logical_intent_id || task.intent_id;
  const targets = task.target_devices.map((device) => device.hostname).join(', ') || task.target_refs.join(', ') || 'Unresolved target';
  return (
    <button type="button" role="option" aria-selected={selected} className={`review-task-row${selected ? ' is-selected' : ''}`} onClick={onSelect}>
      <span className="review-task-row__top"><strong>{task.operation_id || 'Unresolved operation'}</strong><StatusBadge status={task.status} /></span>
      <span><Server size={12} />{targets}</span>
      <small>Task {task.intent_id}</small>
      <small>Intent {intentId}</small>
    </button>
  );
}

function TaskDetails({ task }: { task: PlanningTask }) {
  const { localPlanning } = useWorkbench();
  const plan = localPlanning.state.result?.session.plan;
  const intentId = task.logical_intent_id || task.intent_id;
  const intent = plan?.intents?.find((item) => item.intent_id === intentId);
  const questions = localPlanning.state.result?.session.pending_questions.filter((question) => question.task_id === task.intent_id) ?? [];
  const planningIssues = task.planning_issues ?? [];
  const parameterEntries = Object.entries(task.parameters);
  const evidence = task.parameter_evidence ?? {};
  const provenance = task.parameter_provenance ?? {};

  return (
    <article className="task-details" aria-label={`Task details ${task.intent_id}`}>
      <header className="task-details__header">
        <div><span className="eyebrow">Selected V9 task</span><h3>{task.operation_id || 'Operation unresolved'}</h3></div>
        <StatusBadge status={task.status} />
      </header>
      <div className="task-identity-grid">
        <div><span>Task ID</span><code>{task.intent_id}</code></div>
        <div><span>Intent ID</span><code>{intentId}</code></div>
        <div><span>Category</span><strong>{task.category || 'Not reported'}</strong></div>
        <div><span>Task revision</span><strong>{task.revision ?? 'Not reported'}</strong></div>
      </div>
      {(intent?.request_text || task.request_text) && <p className="intent-request"><Network size={14} /><span><strong>Intent request</strong>{intent?.request_text || task.request_text}</span></p>}
      {task.feedback && <div className="task-feedback" role="note"><AlertTriangle size={14} /><span><strong>V9 feedback</strong>{task.feedback}</span></div>}

      <section className="review-section" aria-label="Resolved targets">
        <h4><Server size={14} />Resolved targets <span>{task.target_devices.length}</span></h4>
        {task.target_devices.length ? <div className="target-grid">{task.target_devices.map((device) => (
          <article className="target-card" key={device.id}>
            <strong>{device.hostname}</strong><span>{device.vendor} · {device.platform}{device.version ? ` ${device.version}` : ''}</span><code>{device.id}</code>
          </article>
        ))}</div> : <div className="review-empty"><CircleDashed size={15} />V9 did not resolve a device. Target references: {task.target_refs.join(', ') || 'none reported'}.</div>}
      </section>

      <section className="review-section" aria-label="Extracted parameters">
        <h4>Extracted parameters <span>{parameterEntries.length}</span></h4>
        {parameterEntries.length ? <div className="parameter-table">{parameterEntries.map(([name, value]) => (
          <div className="parameter-row" key={name}>
            <code>{name}</code><pre>{json(value)}</pre>
            <div><span>Provenance</span><code>{provenance[name] || 'Not reported'}</code></div>
            <div><span>Evidence</span><pre>{evidence[name] === undefined ? 'Not reported' : json(evidence[name])}</pre></div>
          </div>
        ))}</div> : <div className="review-empty">No extracted parameters were returned for this task.</div>}
      </section>

      <IssueList title="Planning issues" issues={planningIssues} />
      <IssueList title="Validation issues" issues={task.issues} />

      {questions.length > 0 && <section className="review-section" aria-label="Pending task clarifications">
        <h4><CircleDashed size={14} />Pending clarifications <span>{questions.length}</span></h4>
        {questions.map((question) => <article className="question-card" key={question.question_id}>
          <strong>{question.wording}</strong><span>{question.field_path}</span><code>{question.question_id}</code>
        </article>)}
        <p className="review-hint">Answer the current question in AI Copilot. This review surface does not advance the session.</p>
      </section>}

      <section className="review-section" aria-label="Generated configuration previews">
        <h4><FileCode2 size={14} />Generated configurations <span>{task.configs.length}</span></h4>
        {task.configs.length ? task.configs.map((config, index) => (
          <article className="generated-preview" key={`${textField(config, 'device_id')}:${index}`}>
            <div><strong>{textField(config, 'hostname') || textField(config, 'device_id') || `Output ${index + 1}`}</strong>
              <span>{[textField(config, 'vendor'), textField(config, 'platform'), textField(config, 'version')].filter(Boolean).join(' · ')}</span>
              <span className="readonly-badge"><CheckCircle2 size={11} /> READ-ONLY V9 OUTPUT</span></div>
            {typeof config.configuration === 'string'
              ? <pre>{config.configuration}</pre>
              : <div className="review-empty">No configuration text was returned for this output record.</div>}
          </article>
        )) : <div className="review-empty">No generated configuration is present for this task. Status: {task.status}.</div>}
      </section>
    </article>
  );
}

export function TaskReviewPanel() {
  const { state, dispatch, localPlanning } = useWorkbench();
  const result = localPlanning.state.result;
  if (!result) return <div className="empty-state"><Network /><span>Create a Local V9 session to review its structured tasks.</span></div>;
  const { plan } = result.session;
  const selected = plan.tasks.find((task) => task.intent_id === state.selectedPlanningTaskId) ?? plan.tasks[0];
  const intentCounts = plan.tasks.reduce<Record<string, number>>((counts, task) => {
    const key = task.logical_intent_id || task.intent_id;
    counts[key] = (counts[key] ?? 0) + 1;
    return counts;
  }, {});
  return (
    <div className="plan-review" aria-label="Local V9 plan review">
      <header className="plan-review__summary">
        <div><span className="message-provenance">LOCAL V9 · PREVIEW ONLY · NOT DEPLOYED</span>
          {localPlanning.state.historical && <p className="saved-state-notice">Saved historical state · current validity not checked</p>}
          <h2>{plan.original_prompt}</h2></div>
        <div className="plan-review__facts"><StatusBadge status={plan.status} /><span>{Object.keys(intentCounts).length} intent(s)</span><span>{plan.tasks.length} task(s)</span></div>
      </header>
      {plan.issues.length > 0 && <IssueList title="Plan-level issues" issues={plan.issues} />}
      {plan.tasks.length ? <div className="plan-review__body">
        <aside className="review-task-list" aria-label="V9 task list">
          <div className="review-task-list__heading"><strong>Tasks</strong><span>Select to inspect</span></div>
          <div role="listbox" aria-label={`${plan.tasks.length} V9 planning tasks`}>
            {plan.tasks.map((task) => <TaskListItem key={task.intent_id} task={task} selected={task.intent_id === selected?.intent_id}
              onSelect={() => dispatch({ type: 'SELECT_PLANNING_TASK', taskId: task.intent_id })} />)}
          </div>
        </aside>
        {selected && <TaskDetails task={selected} />}
      </div> : <div className="empty-state"><AlertTriangle /><span>V9 returned no tasks for this session.</span></div>}
    </div>
  );
}

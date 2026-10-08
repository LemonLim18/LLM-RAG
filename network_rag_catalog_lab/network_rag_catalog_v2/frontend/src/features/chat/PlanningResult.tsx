import type { PlanningResponse } from '../../services/planningApi';

function JsonDetails({ label, value }: { label: string; value: unknown }) {
  return <details><summary>{label}</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>;
}

export function PlanningResult({ result }: { result: PlanningResponse }) {
  const { session } = result;
  return (
    <section className="planning-result" aria-label="Local V9 session result">
      <span className="message-provenance">LOCAL V9 · SYNTHETIC INVENTORY · PREVIEW ONLY</span>
      <h3>Session: {session.status}</h3>
      <p className="planning-id">{session.session_id}</p>
      <p>Authority: {session.plan.runtime_authority || 'not reported'}</p>
      <p>Knowledge snapshot: {session.plan.knowledge_snapshot_id || 'none (no published snapshot)'}</p>
      <p>V9 may use deterministic fallbacks. This result alone does not prove model or RAG participation.</p>
      {session.plan.issues.length > 0 && <JsonDetails label="Plan issues" value={session.plan.issues} />}
      <h3>{session.plan.tasks.length} task(s)</h3>
      {session.plan.tasks.length === 0 && <p>No tasks were returned by V9.</p>}
      {session.plan.tasks.map((task) => (
        <article className="planning-task" key={task.intent_id}>
          <h4>{task.operation_id || 'Unresolved operation'} · {task.status}</h4>
          <p className="planning-id">Task: {task.intent_id}</p>
          {task.feedback && <p role="note">V9 feedback: {task.feedback}</p>}
          <p>Targets: {task.target_devices.map((device) => `${device.hostname} / ${device.vendor} ${device.platform} (${device.id})`).join(', ') || task.target_refs.join(', ') || 'Unresolved'}</p>
          <strong>Parameters</strong><pre>{JSON.stringify(task.parameters, null, 2)}</pre>
          {task.issues.length > 0 && <JsonDetails label="Validation issues" value={task.issues} />}
          {task.configs.length > 0 && <JsonDetails label="Generated configuration (read-only preview)" value={task.configs} />}
          <JsonDetails label="Task evidence, target resolution and revisions" value={task} />
        </article>
      ))}
      {session.pending_questions.length > 0 && (
        <section aria-label="Pending clarification">
          <h3>Clarification required</h3>
          <p>Answering questions is not supported in Iteration 4. No answer has been submitted.</p>
          {session.pending_questions.map((question) => (
            <article className="planning-task" key={question.question_id}>
              <p>{String(question.wording || question.question || question.prompt || question.label || question.field_path || 'Pending question')}</p>
              <p className="planning-id">Question: {question.question_id} · Task: {question.task_id}</p>
              <JsonDetails label="Question and options" value={question} />
            </article>
          ))}
        </section>
      )}
      <JsonDetails label="Full serialized V9 session" value={result} />
    </section>
  );
}

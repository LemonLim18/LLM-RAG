import type { SessionSnapshot } from '../../services/planningApi';
import { useWorkbench } from '../../app/workbenchContext';
import { ClarificationForm } from './ClarificationForm';
import { GeneratedWorkingAction } from '../workspace/GeneratedWorkingAction';

export function PlanningResult({ result }: { result: SessionSnapshot }) {
  const { session } = result;
  const { dispatch, localPlanning, working } = useWorkbench();
  const answer = localPlanning.answerState;
  const question = session.pending_questions[0];
  const editableError = ['INVALID_OPTION', 'CUSTOM_NOT_ALLOWED', 'V9_ANSWER_REJECTED'].includes(answer.error?.code || '');
  const retryable = ['OUTCOME_UNKNOWN', 'REQUEST_IN_PROGRESS', 'PLANNER_BUSY'].includes(answer.error?.code || '');
  return (
    <section className="planning-result" aria-label="Local V9 session result">
      <span className="message-provenance">LOCAL V9 · SYNTHETIC INVENTORY · PREVIEW ONLY</span>
      <h3>Session: {session.status}</h3>
      <p className="planning-id">{session.session_id}</p>
      {localPlanning.state.historical && <p className="saved-state-notice" role="note">Retrieved historical session · freshness and mutation eligibility not checked. Saved ready/rendered output has not been revalidated. Any answer must pass V9's current checks.</p>}
      <details><summary>Saved revision and history</summary>
        <p className="planning-id">{result.session_revision}</p>
        <pre>{JSON.stringify({ source_revision: session.plan.source_revision, context_revision: session.plan.context_revision,
          history: session.history, answer_history: session.plan.tasks.map((task) => ({ task_id: task.intent_id, history: task.clarification_history })) }, null, 2)}</pre>
      </details>
      <p>Authority: {session.plan.runtime_authority || 'not reported'}</p>
      <p>Knowledge snapshot: {session.plan.knowledge_snapshot_id || 'none (no published snapshot)'}</p>
      <p>V9 may use deterministic fallbacks. This result alone does not prove model or RAG participation.</p>
      <div className="planning-summary">
        <strong>{session.plan.tasks.length} task(s)</strong>
        <span>{session.plan.intents?.length ?? new Set(session.plan.tasks.map((task) => task.logical_intent_id || task.intent_id)).size} intent(s)</span>
        <button type="button" onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'plan' })}>Review plan in workspace</button>
      </div>
      <div className="working-output-links">
        {session.plan.tasks.map((task) => task.configs.map((_, index) => <GeneratedWorkingAction key={`${task.intent_id}:${index}`} result={result} task={task} index={index} />))}
        {working.opening.message && <p role="status">{working.opening.message}</p>}
      </div>
      {answer.phase === 'pending' && <p role="status">Submitting answer to V9… Last confirmed session remains below.</p>}
      {answer.phase === 'success' && <p role="status">Answer accepted by V9. Showing the updated saved session.</p>}
      {answer.request && <p className="planning-id">Answer request: {answer.request.client_request_id}</p>}
      {answer.phase === 'error' && <div className="planning-error" role="alert">
        <p>{answer.error?.code}: {answer.error?.message}</p>
        <p>No acceptance is assumed. The last confirmed session is retained.</p>
        {editableError && <button type="button" disabled={localPlanning.busy} onClick={localPlanning.editAnswer}>Review and edit answer</button>}
        {retryable && <><p>Retry only in the same backend process; timeout does not cancel V9. Do not create another answer ID.</p>
          <button type="button" disabled={localPlanning.busy} onClick={localPlanning.retryAnswer}>Retry same answer request</button></>}
        {!editableError && !retryable && <p>Answering is blocked. Read the latest saved state to inspect it; this does not resume or refresh the session.</p>}
      </div>}
      {question && session.status === 'needs_clarification' && <ClarificationForm
        key={`${session.session_id}:${question.question_id}:${question.revision}`}
        question={question} disabled={localPlanning.busy || localPlanning.recovery.uncertain || answer.phase === 'error'} onAnswer={localPlanning.answer} />}
      {session.plan.issues.length > 0 && <p role="note">{session.plan.issues.length} plan-level issue(s) are shown in the workspace review.</p>}
      {session.plan.tasks.length === 0 && <p>No tasks were returned by V9.</p>}
      {session.pending_questions.length > 0 && (
        <section aria-label="Pending clarification">
          <h3>Clarification required</h3>
          <p>Only the current question can be answered. Further questions remain pending until you answer them explicitly.</p>
          {session.pending_questions.map((question) => (
            <article className="planning-task" key={question.question_id}>
              <p>{String(question.wording || question.question || question.prompt || question.label || question.field_path || 'Pending question')}</p>
              <p className="planning-id">Question: {question.question_id} · Task: {question.task_id}</p>
            </article>
          ))}
        </section>
      )}
    </section>
  );
}

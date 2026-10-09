import type { AnswerValue, Json, SessionSnapshot } from '../../services/planningApi';

export const recoveryKey = 'v9.session-recovery.v1';
export interface RecoveryReference { sessionId: string; revision: string; answerUncertain: boolean }
export interface RecoveryMetadata { reference?: RecoveryReference; unknownCreationRequestId?: string }
export const isSessionId = (value: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);

export function readRecoveryMetadata(): RecoveryMetadata {
  try {
    const data = JSON.parse(localStorage.getItem(recoveryKey) || '{}');
    const reference = data?.reference;
    return {
      reference: isSessionId(reference?.sessionId || '') && /^[a-f0-9]{64}$/.test(reference?.revision || '')
        ? { sessionId: reference.sessionId, revision: reference.revision, answerUncertain: reference.answerUncertain === true } : undefined,
      unknownCreationRequestId: isSessionId(data?.unknownCreationRequestId || '') ? data.unknownCreationRequestId : undefined,
    };
  } catch { return {}; }
}

export function saveRecoveryMetadata(data: RecoveryMetadata): boolean {
  try {
    if (!data.reference && !data.unknownCreationRequestId) localStorage.removeItem(recoveryKey);
    else localStorage.setItem(recoveryKey, JSON.stringify(data));
    return true;
  } catch { return false; }
}

function record(value: unknown): Record<string, Json> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, Json> : undefined;
}

// Match persisted V9 evidence, never revision change alone. The HTTP request UUID
// is not persisted by V9, so this identifies the recorded answer, not its sender.
export function recordedAnswerOutcome(before: SessionSnapshot, after: SessionSnapshot, answer: AnswerValue): 'accepted' | 'rejected' | undefined {
  if (before.session.session_id !== after.session.session_id) return;
  const question = before.session.pending_questions.find((item) => item.question_id === answer.question_id);
  const priorTask = before.session.plan.tasks.find((task) => task.intent_id === question?.task_id);
  const task = after.session.plan.tasks.find((item) => item.intent_id === question?.task_id);
  if (!priorTask || !task || !Array.isArray(priorTask.clarification_history) || !Array.isArray(task.clarification_history)) return;
  const entries = task.clarification_history.slice(priorTask.clarification_history.length);
  const matches = entries.map(record).filter((entry) => {
    const saved = record(entry?.answer);
    return saved && saved.question_id === answer.question_id && saved.revision === answer.revision
      && saved.source_revision === answer.source_revision && saved.kind === answer.kind
      && saved.raw_input === answer.raw_input && JSON.stringify(saved.selected_ids) === JSON.stringify(answer.selected_ids);
  });
  if (matches.length !== 1) return;
  return matches[0]?.accepted === true ? 'accepted' : matches[0]?.accepted === false ? 'rejected' : undefined;
}

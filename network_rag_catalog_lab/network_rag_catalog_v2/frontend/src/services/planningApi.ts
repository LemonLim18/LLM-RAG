import { apiBaseUrl } from './runtimeApi';

export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };
export interface ClarificationQuestion {
  question_id: string;
  task_id: string;
  revision: number;
  source_revision: string;
  wording: string;
  field_path: string;
  multiple: boolean;
  allow_custom: boolean;
  expected_schema: Record<string, Json>;
  options: Array<{ option_id: string; value: Json; label: string; explanation?: string; source_ref?: string }>;
  [field: string]: unknown;
}
export interface PlanningTask {
  intent_id: string;
  logical_intent_id?: string;
  request_text?: string;
  category?: string;
  operation_id: string;
  device_id: string | null;
  status: string;
  feedback: string;
  parameters: Record<string, Json>;
  parameter_provenance?: Record<string, string>;
  parameter_evidence?: Record<string, Json>;
  target_refs: string[];
  target_devices: Array<{ id: string; hostname: string; vendor: string; platform: string; version?: string }>;
  target_resolution?: Array<Record<string, Json>>;
  issues: Array<Record<string, Json>>;
  planning_issues?: Array<Record<string, Json>>;
  configs: Array<Record<string, Json>>;
  revision?: number;
  source_revision?: string;
  [field: string]: unknown;
}
export interface PlanningIntent {
  intent_id: string;
  request_text: string;
  target_refs: string[];
  target_text: string;
  source_spans: Array<Record<string, Json>>;
  issues: Array<Record<string, Json>>;
}
export interface SessionSnapshot {
  api_version: 1;
  mode: 'local_v9';
  inventory_source: 'synthetic';
  session_revision: string;
  session: {
    session_id: string;
    status: string;
    plan: {
      original_prompt: string;
      status: string;
      runtime_authority: string;
      knowledge_snapshot_id: string;
      issues: Array<Record<string, Json>>;
      intents?: PlanningIntent[];
      tasks: PlanningTask[];
      [field: string]: unknown;
    };
    pending_questions: ClarificationQuestion[];
    [field: string]: unknown;
  };
}
export interface PlanningResponse extends SessionSnapshot {
  client_request_id: string;
}
export interface SavedSessionResponse extends SessionSnapshot {
  origin: 'saved_session';
  freshness: 'not_checked';
  mutation_eligibility: 'not_checked';
}
export interface CreationOutcome {
  api_version: 1;
  client_request_id: string;
  status: 'unknown' | 'in_progress' | 'completed' | 'terminal_error' | 'indeterminate' | 'corrupt';
  message: string;
  session_id: string | null;
  session_revision: string | null;
  error_code: string | null;
}
export async function readCreationOutcome(requestId: string): Promise<CreationOutcome> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/planning/requests/${encodeURIComponent(requestId)}`, {
      headers: { Accept: 'application/json' }, cache: 'no-store', signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new Error('Creation outcome lookup is unavailable. No creation was replayed. You can retry this read.');
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(`${body?.detail?.code || 'OUTCOME_READ_FAILED'}: ${body?.detail?.message || 'Unable to check creation outcome.'}`);
  if (body?.api_version !== 1 || body.client_request_id !== requestId || typeof body.message !== 'string'
      || !['unknown', 'in_progress', 'completed', 'terminal_error', 'indeterminate', 'corrupt'].includes(body.status)
      || (body.status === 'completed' && (!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(body.session_id ?? '')
        || !/^[a-f0-9]{64}$/.test(body.session_revision ?? '')))) {
    throw new Error('Invalid creation-outcome response. No session was adopted or creation replayed.');
  }
  return body as CreationOutcome;
}
export async function readSavedSession(sessionId: string): Promise<SavedSessionResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/planning/sessions/${encodeURIComponent(sessionId)}`, {
      headers: { Accept: 'application/json' }, cache: 'no-store', signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new Error('Saved session is unavailable. Retrieval did not request any mutation. You can retry the read.');
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(`${body?.detail?.code || 'SESSION_READ_FAILED'}: ${body?.detail?.message || 'Unable to read saved session.'}`);
  if (body?.origin !== 'saved_session' || body.session?.session_id !== sessionId
      || !/^[a-f0-9]{64}$/.test(body.session_revision) || body.freshness !== 'not_checked'
      || body.mutation_eligibility !== 'not_checked' || !Array.isArray(body.session?.plan?.tasks)
      || !Array.isArray(body.session?.pending_questions)) {
    throw new Error('Invalid saved-session response. The current workbench state was retained.');
  }
  return body as SavedSessionResponse;
}
export interface PlanningRequest {
  prompt: string;
  mode: 'local_v9';
  client_request_id: string;
}

export interface AnswerValue {
  question_id: string;
  revision: number;
  source_revision: string;
  kind: 'selection' | 'custom';
  raw_input: string;
  selected_ids: string[];
}
export interface AnswerRequest {
  client_request_id: string;
  expected_session_revision: string;
  answer: AnswerValue;
}
export interface AnswerResponse extends PlanningResponse {
  accepted: true;
  answered_question_id: string;
}
export class AnswerError extends Error {
  constructor(public code: string, message: string, public currentSession?: PlanningResponse) {
    super(message);
  }
}

export async function submitClarification(sessionId: string, request: AnswerRequest): Promise<AnswerResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/planning/sessions/${encodeURIComponent(sessionId)}/answers`, {
      method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(request), signal: AbortSignal.timeout(120_000),
    });
  } catch {
    throw new AnswerError('OUTCOME_UNKNOWN', 'Connection lost or timed out. V9 may still save the answer. Retry only this same request while the backend process remains unchanged.');
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new AnswerError(body?.detail?.code || 'ANSWER_REQUEST_FAILED',
      body?.detail?.message || `Answer request failed (HTTP ${response.status}). No acceptance confirmed.`,
      body?.detail?.current_session || undefined);
  }
  if (!body || body.accepted !== true || body.answered_question_id !== request.answer.question_id
      || body.session?.session_id !== sessionId || body.client_request_id !== request.client_request_id) {
    throw new AnswerError('OUTCOME_UNKNOWN', 'Unexpected answer response. Keep the last confirmed session and inspect the saved outcome before retrying.');
  }
  return body as AnswerResponse;
}

export async function createPlanningSession(request: PlanningRequest): Promise<PlanningResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/planning/sessions`, {
      method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(request), signal: AbortSignal.timeout(120_000),
    });
  } catch {
    throw new Error('Backend unavailable or request timed out. The outcome is unknown; V9 may still save a session.');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(typeof detail?.message === 'string'
      ? `${detail.code}: ${detail.message}` : `Planning request failed (HTTP ${response.status}).`);
  }
  return response.json() as Promise<PlanningResponse>;
}

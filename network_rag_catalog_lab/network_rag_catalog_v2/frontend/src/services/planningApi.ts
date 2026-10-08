import { apiBaseUrl } from './runtimeApi';

export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };
export interface PlanningTask {
  intent_id: string;
  operation_id: string;
  device_id: string | null;
  status: string;
  feedback: string;
  parameters: Record<string, Json>;
  target_refs: string[];
  target_devices: Array<{ id: string; hostname: string; vendor: string; platform: string }>;
  issues: Array<Record<string, Json>>;
  configs: Array<Record<string, Json>>;
  [field: string]: unknown;
}
export interface PlanningResponse {
  api_version: 1;
  mode: 'local_v9';
  inventory_source: 'synthetic';
  client_request_id: string;
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
      tasks: PlanningTask[];
      [field: string]: unknown;
    };
    pending_questions: Array<{ question_id: string; task_id: string; [field: string]: Json }>;
    [field: string]: unknown;
  };
}
export interface PlanningRequest {
  prompt: string;
  mode: 'local_v9';
  client_request_id: string;
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

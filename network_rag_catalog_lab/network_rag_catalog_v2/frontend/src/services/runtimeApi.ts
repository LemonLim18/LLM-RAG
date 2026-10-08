export type CheckState = 'not_checked';

export interface HealthResponse {
  status: 'ok';
  service: 'network-rag-workbench';
  api_version: 1;
}

export interface PassiveCheck {
  status: CheckState;
  configured_model: string | null;
  reason: string;
}

export interface RuntimeStatusResponse {
  api_version: 1;
  service: 'ready';
  knowledge: {
    status: 'ready' | 'unavailable';
    configured_runtime_mode: 'files' | 'published' | null;
    effective_runtime_authority: 'direct_files' | 'published_release' | null;
    authoring_authority: 'json' | 'sqlite' | null;
    active_release_id: string | null;
    error_code: string | null;
  };
  llm: PassiveCheck;
  embeddings: PassiveCheck;
  retrieval: PassiveCheck;
}

export interface BackendSnapshot {
  health: HealthResponse;
  runtime: RuntimeStatusResponse;
}

export class BackendResponseError extends Error {
  constructor(public readonly status: number) {
    super(`Backend returned HTTP ${status}.`);
  }
}

export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');

export async function readApiJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!response.ok) throw new BackendResponseError(response.status);
  return response.json() as Promise<T>;
}

export async function readBackendSnapshot(signal: AbortSignal): Promise<BackendSnapshot> {
  const [health, runtime] = await Promise.all([
    readApiJson<HealthResponse>('/health', signal),
    readApiJson<RuntimeStatusResponse>('/runtime/status', signal),
  ]);
  return { health, runtime };
}

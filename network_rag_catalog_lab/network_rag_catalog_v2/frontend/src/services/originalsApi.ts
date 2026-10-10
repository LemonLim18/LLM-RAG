import { apiBaseUrl } from './runtimeApi';
import type { GeneratedPreviewSelection } from '../app/types';

export interface OriginalMetadata {
  schema_version: 1;
  kind: 'generated_original';
  artifact_id: string;
  source: { session_id: string; session_revision: string; task_id: string; device_id: string; config_index: number };
  logical_intent_id: string | null;
  operation_id: string | null;
  category: string | null;
  hostname: string | null;
  vendor: string | null;
  platform: string | null;
  version: string | null;
  captured_at: string;
  content_sha256: string;
  content_encoding: 'utf-8';
  authority: Record<string, string | null>;
  validity: 'historical_not_checked';
}
export interface GeneratedOriginal extends OriginalMetadata { configuration: string; record_sha256: string }
export interface CaptureResponse { api_version: 1; outcome: 'created' | 'already_saved'; artifact: GeneratedOriginal }
const base = '/workbench/artifacts/generated-originals';

export class OriginalError extends Error {
  constructor(public code: string, message: string) { super(message); }
}
async function request<T>(path: string, body?: object): Promise<T> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      method: body ? 'POST' : 'GET', headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(15_000), cache: 'no-store',
    });
    const data = await response.json();
    if (!response.ok) throw new OriginalError(data?.detail?.code || `HTTP_${response.status}`,
      data?.detail?.message || 'The original request was rejected. Check the selected source and backend.');
    return data as T;
  } catch (error) {
    if (error instanceof OriginalError) throw error;
    throw new OriginalError(body ? 'OUTCOME_UNCERTAIN' : 'ORIGINALS_UNAVAILABLE', body
      ? 'Capture outcome is uncertain; it may have saved. Refresh Saved Originals to inspect the outcome. No automatic retry was made.'
      : 'Saved Originals could not be read. Check the backend and refresh.');
  }
}
export const listOriginals = () => request<{ api_version: 1; limit: number; artifacts: OriginalMetadata[] }>(base);
export const readOriginal = (id: string) => request<GeneratedOriginal>(`${base}/${encodeURIComponent(id)}`);
export async function captureOriginal(selection: GeneratedPreviewSelection): Promise<CaptureResponse> {
  const result = await request<CaptureResponse>(base, {
    session_id: selection.sessionId, expected_session_revision: selection.sessionRevision,
    task_id: selection.taskId, device_id: selection.deviceId, config_index: selection.configIndex,
  });
  const source = result.artifact?.source;
  if (result.api_version !== 1 || !['created', 'already_saved'].includes(result.outcome)
      || source?.session_id !== selection.sessionId || source?.session_revision !== selection.sessionRevision
      || source?.task_id !== selection.taskId || source?.device_id !== selection.deviceId || source?.config_index !== selection.configIndex) {
    throw new OriginalError('OUTCOME_UNCERTAIN', 'Unexpected capture confirmation. Refresh Saved Originals to inspect the outcome before another capture.');
  }
  return result;
}

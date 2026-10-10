import { apiBaseUrl } from './runtimeApi';
import type { OriginalMetadata } from './originalsApi';

export interface WorkingMetadata {
  schema_version: 1; document_id: string; original: OriginalMetadata; revision: string;
  save_sequence: number; created_at: string; updated_at: string; content_sha256: string;
  encoding: 'utf-8'; validation: 'unvalidated'; deployment: 'not_deployed';
}
export interface WorkingDocument extends WorkingMetadata { content: string; record_sha256: string }
export class WorkingError extends Error {
  constructor(public code: string, message: string) { super(message); }
}
const base = `${apiBaseUrl}/workbench/working-documents`;
async function request<T>(path: string, method = 'GET', body?: object): Promise<T> {
  try {
    const response = await fetch(`${base}${path}`, { method, cache: 'no-store', signal: AbortSignal.timeout(15_000),
      headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined });
    const data = await response.json();
    if (!response.ok) throw new WorkingError(data?.detail?.code || `HTTP_${response.status}`,
      data?.detail?.message || 'Working document request rejected. Local edits were retained.');
    return data as T;
  } catch (error) {
    if (error instanceof WorkingError) throw error;
    throw new WorkingError(method === 'GET' ? 'WORKING_UNAVAILABLE' : 'OUTCOME_UNCERTAIN', method === 'GET'
      ? 'Working Files could not be read. Check the backend and refresh.'
      : 'Outcome uncertain: the write may have committed. Refresh Working Files or inspect saved state. No automatic retry was made.');
  }
}
function checked(document: WorkingDocument, id?: string) {
  if (!document || !/^working-[a-f0-9]{64}$/.test(document.document_id)
      || document.document_id !== document.original?.artifact_id.replace('original-', 'working-')
      || (id && document.document_id !== id) || typeof document.content !== 'string'
      || !/^[a-f0-9-]{36}$/.test(document.revision) || document.validation !== 'unvalidated'
      || document.deployment !== 'not_deployed' || document.schema_version !== 1) {
    throw new WorkingError('OUTCOME_UNCERTAIN', 'Unexpected document confirmation. Inspect saved state; local edits were retained.');
  }
  return document;
}
export const listWorking = () => request<{ api_version: 1; documents: WorkingMetadata[]; limit: number }>('');
export async function readWorking(id: string) { return checked(await request<WorkingDocument>(`/${encodeURIComponent(id)}`), id); }
export async function openWorking(originalId: string) {
  const result = await request<{ api_version: 1; outcome: 'created' | 'reopened'; document: WorkingDocument }>('', 'POST', { original_id: originalId });
  return checked(result.document, originalId.replace('original-', 'working-'));
}
export async function saveWorking(id: string, revision: string, content: string) {
  const result = checked(await request<WorkingDocument>(`/${encodeURIComponent(id)}`, 'PUT', { expected_revision: revision, content }), id);
  if (result.revision === revision || result.content !== content) throw new WorkingError('OUTCOME_UNCERTAIN', 'Unexpected save confirmation. Inspect saved state before retrying.');
  return result;
}

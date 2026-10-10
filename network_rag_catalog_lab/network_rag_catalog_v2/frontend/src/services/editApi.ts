import { apiBaseUrl } from './runtimeApi';
import { WorkingError } from './workingApi';
import type { ProposalBase } from '../features/workspace/changeReview';

export interface EditResult {
  api_version: 1; document_id: string; base_revision: string; base_content_sha256: string; proposal_id: string;
  outcome: 'proposal' | 'no_change' | 'clarification_required' | 'unsupported'; message: string;
  proposed_content: string | null; operation_id: string; parameters: Record<string, string | number>;
  evidence: Record<string, string>; authority: Record<string, string | null>;
  validation: 'bounded_operation_only'; deployment: 'not_deployed';
}
export async function proposeEdit(base: ProposalBase, instruction: string): Promise<EditResult> {
  try {
    const response = await fetch(`${apiBaseUrl}/workbench/working-documents/${encodeURIComponent(base.documentId)}/propose-edit`, {
      method: 'POST', cache: 'no-store', signal: AbortSignal.timeout(45_000),
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ expected_revision: base.baseRevision, current_content: base.baseContent, instruction }),
    });
    const value = await response.json() as EditResult & { detail?: { code?: string; message?: string } };
    if (!response.ok) throw new WorkingError(value.detail?.code ?? `HTTP_${response.status}`, value.detail?.message ?? 'Edit request rejected. No local change was applied.');
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(base.baseContent))), (b) => b.toString(16).padStart(2, '0')).join('');
    if (value.api_version !== 1 || value.document_id !== base.documentId || value.base_revision !== base.baseRevision ||
        value.base_content_sha256 !== digest || !/^[a-f0-9-]{36}$/.test(value.proposal_id) ||
        !['proposal', 'no_change', 'clarification_required', 'unsupported'].includes(value.outcome) ||
        typeof value.message !== 'string' || value.validation !== 'bounded_operation_only' || value.deployment !== 'not_deployed' ||
        (value.outcome === 'no_change' && value.proposed_content !== base.baseContent) ||
        (['proposal', 'no_change'].includes(value.outcome) && typeof value.proposed_content !== 'string')) {
      throw new WorkingError('INVALID_EDIT_RESPONSE', 'Response does not match the captured document. Nothing was staged.');
    }
    return value;
  } catch (error) {
    if (error instanceof WorkingError) throw error;
    throw new WorkingError('EDIT_RESPONSE_UNAVAILABLE', 'No edit response was confirmed. Inference may still be running, but this endpoint cannot save or apply edits. No automatic retry was made.');
  }
}

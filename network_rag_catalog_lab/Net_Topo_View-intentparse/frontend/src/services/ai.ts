import { request } from './api';

export interface EditorSnapshot {
  document_id: string; path: string; content: string; language: string;
  model_id: string; model_version: number; buffer_epoch: number; saved_revision: number;
  is_dirty: boolean; read_only: boolean; device_id?: string;
  selection?: { text: string; start_line: number; end_line: number };
}
export interface EditProposal {
  id: string; document_id: string; path: string; model_id: string; model_version: number;
  buffer_epoch: number; saved_revision: number; base_digest: string;
  original: string; suggested: string; validation: Record<string, unknown>; reference?: {path:string;content:string};
}
export interface DraftDocument {
  id: string; path: string; content: string; device_id: string; task_id?: string; documents?: DraftDocument[]; reference?: {path:string;content:string}; validation: Record<string, unknown>;
}
export interface AIEvidence { id: string; source: string; origin: string; authority: string; device_refs?: string[]; captured_at?: string; freshness?: string; time_scope?: string; page?: number; start_line?: number; end_line?: number }
export interface AIResponse {
  request_id: string; status: string; kind: string; answer: string; model?: string;
  evidence: AIEvidence[]; context_coverage: { complete?: boolean; included_characters?: number; total_characters?: number };
  preview?: any; proposal?: EditProposal;
}
export interface AIConversation {
  id: string; assistant_kind: 'floating' | 'studio'; title: string; updatedAt: string;
  messages: { id: string; role: string; content: string; timestamp: number; evidence?: AIEvidence[]; evidence_details?: string }[];
}
export const aiApi = {
  handoffEligibility: (id:string,turn:string) => request<any>(`/ai/conversations/${encodeURIComponent(id)}/turns/${encodeURIComponent(turn)}/handoff-eligibility`),
  prepareHandoff: (id:string,source_turn:string,requested_action:string) => request<any>(`/ai/conversations/${encodeURIComponent(id)}/handoffs`, {method:'POST',body:JSON.stringify({source_turn,requested_action})}),
  acceptHandoff: (id:string) => request<{conversation_id:string;draft:string;warning?:string}>(`/ai/handoffs/${id}/accept`, {method:'POST'}),
  create: (assistant_kind: 'floating' | 'studio', id?: string) => request<AIConversation>('/ai/conversations', { method: 'POST', body: JSON.stringify({ assistant_kind, id }) }),
  list: (kind: 'floating' | 'studio') => request<{ sessions: AIConversation[] }>(`/ai/conversations?assistant_kind=${kind}`),
  get: (id: string) => request<AIConversation>(`/ai/conversations/${encodeURIComponent(id)}`),
  remove: (id: string) => request(`/ai/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  inventory: () => request<{ status: string; data: { devices: any[]; links: any[]; scenario?: any }; evidence: AIEvidence[] }>('/ai/inventory'),
  saveInventoryMetadata: (id: number, body: { site: string; location: string; aliases: string[] }) => request(`/ai/inventory/${id}/metadata`, { method: 'PUT', body: JSON.stringify(body) }),
  saveEngineeringFacts: (id: number, facts: Record<string, unknown>, expected_revision: string) => request<{revision:string}>(`/ai/inventory/${id}/engineering-facts`, {method:'PUT',body:JSON.stringify({facts,expected_revision})}),
  diagnostics: () => request<any>('/ai/diagnostics'),
  turn: (id: string, body: { request_id: string; prompt: string; model?: string; editor?: EditorSnapshot | null; attachment_ids?: string[] }, signal?: AbortSignal) =>
    request<AIResponse>(`/ai/conversations/${encodeURIComponent(id)}/turns`, { method: 'POST', body: JSON.stringify(body), signal }),
  cancel: (id: string, requestId: string) => request(`/ai/conversations/${encodeURIComponent(id)}/turns/${requestId}/cancel`, { method: 'POST' }),
  upload: (id: string, file: File) => request<{ id: string; name: string; byte_size: number }>(`/ai/conversations/${encodeURIComponent(id)}/attachments`, { method: 'POST', body: file, headers: { 'Content-Type': 'application/octet-stream', 'X-File-Name': encodeURIComponent(file.name) } }),
  removeAttachment: (id: string, attachment: string) => request(`/ai/conversations/${encodeURIComponent(id)}/attachments/${attachment}`, { method: 'DELETE' }),
  listAttachments: (id: string) => request<{ attachments: { id: string; name: string; byte_size: number }[] }>(`/ai/conversations/${encodeURIComponent(id)}/attachments`),
  attachment: (id: string, attachment: string) => request<{ id: string; name: string; content: string }>(`/ai/conversations/${encodeURIComponent(id)}/attachments/${attachment}`),
  save: (path: string, content: string, expected_revision: number, create = false) => request<{ revision: number }>('/ai/documents', { method: 'PUT', body: JSON.stringify({ path, content, expected_revision, create }) }),
  referenceTemplate: (path:string) => request<DraftDocument>('/ai/studio/reference-template?path='+encodeURIComponent(path)),
  catalog: () => request<any>('/ai/studio/catalog'),
  preview: (body: { conversation_id: string; prompt: string; model?: string; output_kind: string; params: Record<string, unknown>; hosts: string[]; task_id?: string; expected_revision?: number; confirm_order?: boolean; refresh_inventory?: boolean; selection?: {task_id?:string;operation_id:string;target_host:string;parameters:Record<string,unknown>;template_id?:string}[] }) => request<any>('/ai/studio/preview', { method: 'POST', body: JSON.stringify(body) }),
  render: (body: { conversation_id: string; session_id: string; expected_revision: number; output_kind: string; model?: string; reference_values?:Record<string,Record<string,string>> }) => request<DraftDocument>('/ai/studio/render', { method: 'POST', body: JSON.stringify(body) }),
};

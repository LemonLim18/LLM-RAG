// Internal integration contract, not an API or a second working-document store.
export interface ProposalBase {
  documentId: string;
  baseRevision: string;
  baseBufferEpoch: number;
  baseContent: string;
}
export interface ChangeProposal extends ProposalBase {
  proposalId: string;
  proposedContent: string;
  source: string;
  description?: string;
}
export interface PendingReview extends ChangeProposal { status: 'pending' | 'stale'; reason?: string }
export interface ReviewOutcome { status: 'staged' | 'accepted' | 'rejected' | 'no_change' | 'refused'; message: string }
export interface WorkingEditorConnection {
  read: () => string;
  replace: (text: string) => boolean;
  focus: () => void;
}

export function validateProposal(proposal: ChangeProposal): string | null {
  if (!proposal || typeof proposal !== 'object' ||
    !['proposalId', 'documentId', 'baseRevision', 'source'].every((key) =>
      typeof proposal[key as keyof ChangeProposal] === 'string' && String(proposal[key as keyof ChangeProposal]).trim().length > 0) ||
    typeof proposal.baseContent !== 'string' || typeof proposal.proposedContent !== 'string' ||
    !Number.isSafeInteger(proposal.baseBufferEpoch) || proposal.baseBufferEpoch < 0 ||
    (proposal.description !== undefined && typeof proposal.description !== 'string')) return 'Invalid proposal contract.';
  if (proposal.proposalId.length > 128 || proposal.source.length > 120 || (proposal.description?.length ?? 0) > 1000 ||
    new TextEncoder().encode(proposal.proposedContent).length > 1024 * 1024) return 'Proposal exceeds the bounded review limits.';
  return null;
}

export function baseMatches(proposal: ProposalBase, current: ProposalBase): boolean {
  return proposal.documentId === current.documentId && proposal.baseRevision === current.baseRevision &&
    proposal.baseBufferEpoch === current.baseBufferEpoch && proposal.baseContent === current.baseContent;
}

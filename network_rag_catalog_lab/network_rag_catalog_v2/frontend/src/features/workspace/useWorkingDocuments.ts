import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { GeneratedPreviewSelection } from '../../app/types';
import { captureOriginal } from '../../services/originalsApi';
import { listWorking, openWorking, readWorking, saveWorking, type WorkingDocument, type WorkingMetadata } from '../../services/workingApi';
import { baseMatches, validateProposal, type ChangeProposal, type PendingReview, type ProposalBase, type ReviewOutcome, type WorkingEditorConnection } from './changeReview';

interface Tab { saved: WorkingDocument; content: string; bufferEpoch: number; saving: boolean; error: string; blocked: boolean; inspected?: WorkingDocument; proposal?: PendingReview; reviewMessage?: string }
const message = (error: unknown) => error instanceof Error ? `${'code' in error ? error.code + ': ' : ''}${error.message}` : 'Document request failed.';
export function useWorkingDocuments(activate: () => void, originalsChanged: () => void, visible: boolean) {
  const [tabs, setTabs] = useState<Record<string, Tab>>({});
  const tabsRef = useRef(tabs);
  const [activeId, setActiveId] = useState('');
  const activeRef = useRef('');
  const visibleRef = useRef(visible);
  const editorRef = useRef<{ id: string; connection: WorkingEditorConnection } | null>(null);
  useLayoutEffect(() => { visibleRef.current = visible; }, [visible]);
  const select = (id: string) => { activeRef.current = id; visibleRef.current = true; setActiveId(id); activate(); };
  const [collection, setCollection] = useState<{ items: WorkingMetadata[]; error: string; loading: boolean }>({ items: [], error: '', loading: true });
  const [opening, setOpening] = useState({ pending: false, message: '' });
  const pending = useRef(false);
  const navigation = useRef(0);
  const listRequest = useRef(0);
  const update = (id: string, transform: (tab: Tab) => Tab) => {
    if (!tabsRef.current[id]) return;
    const previous = tabsRef.current[id];
    let next = transform(previous);
    if (next.content !== previous.content) next = { ...next, bufferEpoch: previous.bufferEpoch + 1 };
    if (next.proposal && (next.content !== previous.content || next.saved.revision !== previous.saved.revision)) {
      next = { ...next, proposal: { ...next.proposal, status: 'stale', reason: 'The working buffer or saved revision changed. Reject this proposal and request a new one.' } };
    }
    tabsRef.current = { ...tabsRef.current, [id]: next };
    setTabs(tabsRef.current);
  };
  const refresh = useCallback(async () => {
    const token = ++listRequest.current;
    setCollection((old) => ({ ...old, loading: true, error: '' }));
    try { const result = await listWorking(); if (token === listRequest.current) setCollection({ items: result.documents, error: '', loading: false }); }
    catch (error) { if (token === listRequest.current) setCollection((old) => ({ ...old, loading: false, error: message(error) })); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const dirty = Object.values(tabs).some((tab) => tab.content !== tab.saved.content || tab.saving);
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    if (dirty) window.addEventListener('beforeunload', guard);
    return () => window.removeEventListener('beforeunload', guard);
  }, [dirty]);
  const adopt = (document: WorkingDocument, token: number) => {
    // A late open never overwrites an already-open tab or its unsaved text.
    if (!tabsRef.current[document.document_id]) {
      tabsRef.current = { ...tabsRef.current, [document.document_id]: { saved: document, content: document.content, bufferEpoch: 0, saving: false, error: '', blocked: false } };
      setTabs(tabsRef.current);
    }
    if (token === navigation.current) select(document.document_id);
  };
  const prepare = async (source: string | GeneratedPreviewSelection) => {
    if (pending.current) return;
    pending.current = true;
    const token = ++navigation.current;
    setOpening({ pending: true, message: 'Preparing working file…' });
    let originalId = typeof source === 'string' ? source : '';
    try {
      if (typeof source !== 'string') {
        originalId = (await captureOriginal(source)).artifact.artifact_id;
        originalsChanged();
      }
      const document = await openWorking(originalId);
      adopt(document, token);
      setOpening({ pending: false, message: 'Working file confirmed. Edits are unvalidated and not deployed.' });
      void refresh();
    } catch (error) {
      setOpening({ pending: false, message: `${originalId ? 'Original available; working file not confirmed. ' : ''}${message(error)}` });
    } finally { pending.current = false; }
  };
  const open = async (id: string) => {
    const token = ++navigation.current;
    if (tabsRef.current[id]) { select(id); return; }
    setOpening({ pending: true, message: 'Reading working file…' });
    try { adopt(await readWorking(id), token); if (token === navigation.current) setOpening({ pending: false, message: '' }); }
    catch (error) { if (token === navigation.current) setOpening({ pending: false, message: message(error) }); }
    finally { if (!pending.current) setOpening((old) => ({ ...old, pending: false })); }
  };
  const save = async (id: string) => {
    const tab = tabsRef.current[id];
    if (!tab || tab.saving || tab.blocked || tab.proposal) return;
    const sent = tab.content;
    update(id, (old) => ({ ...old, saving: true, error: '' }));
    try {
      const saved = await saveWorking(id, tab.saved.revision, sent);
      update(id, (old) => ({ ...old, saved, saving: false, inspected: undefined }));
      void refresh();
    } catch (error) { update(id, (old) => ({ ...old, saving: false, blocked: true, error: message(error) })); }
  };
  const inspect = async (id: string) => {
    try { const inspected = await readWorking(id); update(id, (old) => ({ ...old, inspected })); }
    catch (error) { update(id, (old) => ({ ...old, error: message(error) })); }
  };
  const proposalBase = (id: string): ProposalBase | null => {
    const tab = tabsRef.current[id];
    return tab ? { documentId: id, baseRevision: tab.saved.revision, baseBufferEpoch: tab.bufferEpoch, baseContent: tab.content } : null;
  };
  const reviewGuard = (proposal: ChangeProposal): string | null => {
    const tab = tabsRef.current[proposal.documentId];
    const current = proposalBase(proposal.documentId);
    if (!tab || !current || activeRef.current !== proposal.documentId || !visibleRef.current || editorRef.current?.id !== proposal.documentId) return 'The proposal target is not the active working editor. No document was changed.';
    if (tab.saving || tab.blocked) return 'Resolve the pending or uncertain save before reviewing a proposal.';
    if (!baseMatches(proposal, current) || editorRef.current.connection.read() !== tab.content) return 'Stale proposal: saved revision, buffer epoch or exact base text no longer matches.';
    return null;
  };
  const stageProposal = (proposal: ChangeProposal): ReviewOutcome => {
    const error = validateProposal(proposal) ?? reviewGuard(proposal);
    if (error) return { status: 'refused', message: error };
    const tab = tabsRef.current[proposal.documentId];
    if (tab.proposal) return { status: 'refused', message: 'A proposal is already pending. Accept or reject it before staging another.' };
    if (proposal.baseContent === proposal.proposedContent) {
      const message = 'No changes proposed. The working buffer is unchanged.';
      update(proposal.documentId, (old) => ({ ...old, reviewMessage: message }));
      return { status: 'no_change', message };
    }
    // Copy caller-owned input. Later producer mutation cannot change a pending review.
    update(proposal.documentId, (old) => ({ ...old, proposal: { ...proposal, status: 'pending' }, reviewMessage: '' }));
    return { status: 'staged', message: 'Pending review only; working text and saved content are unchanged.' };
  };
  const acceptProposal = (id: string, proposalId: string): ReviewOutcome => {
    const proposal = tabsRef.current[id]?.proposal;
    if (!proposal || proposal.proposalId !== proposalId) return { status: 'refused', message: 'This is not the current pending proposal.' };
    const error = reviewGuard(proposal) ?? (proposal.status === 'stale' ? proposal.reason ?? 'Stale proposal.' : null);
    if (error) {
      update(id, (old) => ({ ...old, proposal: { ...proposal, status: 'stale', reason: error } }));
      return { status: 'refused', message: error };
    }
    if (!editorRef.current!.connection.replace(proposal.proposedContent)) {
      const message = 'Monaco cannot apply this text exactly (for example, a changed BOM, bare CR or mixed line endings). Nothing was accepted.';
      update(id, (old) => ({ ...old, reviewMessage: message }));
      return { status: 'refused', message };
    }
    const message = 'Proposal accepted into the working buffer. Not saved, validated or deployed. Ctrl+Z undoes this edit.';
    update(id, (old) => ({ ...old, content: proposal.proposedContent, proposal: undefined, reviewMessage: message }));
    return { status: 'accepted', message };
  };
  const rejectProposal = (id: string, proposalId: string): ReviewOutcome => {
    if (tabsRef.current[id]?.proposal?.proposalId !== proposalId) return { status: 'refused', message: 'This is not the current pending proposal.' };
    const message = 'Proposal rejected. Your working buffer and saved revision are unchanged.';
    update(id, (old) => ({ ...old, proposal: undefined, reviewMessage: message }));
    return { status: 'rejected', message };
  };
  return { tabs, activeId, collection, opening, refresh, prepare, open, save, inspect,
    proposalBase, stageProposal, acceptProposal, rejectProposal,
    connectEditor: (id: string, connection: WorkingEditorConnection) => {
      const entry = { id, connection }; editorRef.current = entry;
      return () => { if (editorRef.current === entry) editorRef.current = null; };
    },
    cancelFocus: () => { navigation.current++; visibleRef.current = false; },
    allowFocus: () => { visibleRef.current = true; },
    edit: (id: string, content: string) => update(id, (old) => ({ ...old, content })),
    acceptInspection: (id: string, discard: boolean) => update(id, (old) => old.inspected ? {
      ...old, saved: old.inspected, content: discard ? old.inspected.content : old.content, inspected: undefined, blocked: false, error: '',
    } : old),
  };
}

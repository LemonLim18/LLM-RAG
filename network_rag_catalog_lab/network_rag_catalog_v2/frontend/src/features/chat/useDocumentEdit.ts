import { useLayoutEffect, useRef, useState } from 'react';
import { useWorkbench } from '../../app/workbenchContext';
import { proposeEdit, type EditResult } from '../../services/editApi';

export function useDocumentEdit(enabled: boolean) {
  const { state, working } = useWorkbench();
  const [status, setStatus] = useState<{ pending: boolean; message: string; error: boolean; result?: EditResult }>({ pending: false, message: '', error: false });
  const pending = useRef(false);
  const navigation = useRef(0);
  useLayoutEffect(() => { navigation.current++; }, [working.activeId, state.workspaceView, enabled]);
  const tab = working.tabs[working.activeId];
  const available = enabled && state.workspaceView === 'working' && Boolean(tab) && !tab.saving && !tab.blocked && !tab.proposal;
  const submit = async (instruction: string) => {
    if (!available || pending.current) return;
    const base = working.proposalBase(working.activeId);
    if (!base) return;
    const token = navigation.current;
    pending.current = true;
    setStatus({ pending: true, message: 'Local V9 is interpreting this edit. The accepted buffer remains unchanged.', error: false });
    try {
      const result = await proposeEdit(base, instruction);
      if (token !== navigation.current) {
        setStatus({ pending: false, message: 'Edit response discarded because document or mode selection changed. Nothing was staged.', error: true });
      } else if (result.outcome === 'proposal' || result.outcome === 'no_change') {
        const outcome = working.stageProposal({ ...base, proposalId: result.proposal_id, proposedContent: result.proposed_content!,
          source: 'Local V9 · model interpretation + catalog validation', description: result.message });
        setStatus({ pending: false, message: outcome.message, error: outcome.status === 'refused', result });
      } else setStatus({ pending: false, message: result.message, error: false, result });
    } catch (error) {
      setStatus({ pending: false, message: error instanceof Error ? `${'code' in error ? error.code + ': ' : ''}${error.message}` : 'Edit request failed.', error: true });
    } finally { pending.current = false; }
  };
  return { ...status, available, tab, submit };
}

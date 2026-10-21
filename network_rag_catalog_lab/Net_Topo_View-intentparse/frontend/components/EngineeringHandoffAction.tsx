import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, X } from 'lucide-react';
import { aiApi } from '../src/services/ai';
const errorText = (error: unknown) => error instanceof Error ? error.message : String(error);

/** One response, one reviewed transfer. Acceptance never sends an engineering turn. */
export default function EngineeringHandoffAction({conversation, turn, onOpen}: {conversation: string; turn: string; onOpen: () => void}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const [source, setSource] = useState<any>(null);
  const [handoff, setHandoff] = useState<any>(null);
  const [action, setAction] = useState('');
  const epoch = useRef(0);
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => () => {epoch.current += 1;}, []);
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.current?.querySelector<HTMLButtonElement>('button')?.focus();
    return () => previous?.focus();
  }, [open]);
  async function review() {
    const request = ++epoch.current;
    setOpen(true); setBusy(true); setStatus('Preparing…'); setSource(null); setHandoff(null);
    try {
      const checked = await aiApi.handoffEligibility(conversation, turn);
      if (epoch.current !== request) return;
      setSource(checked); setStatus(checked.status);
    } catch (error) {if (epoch.current === request) setStatus(errorText(error));}
    finally {if (epoch.current === request) setBusy(false);}
  }
  async function prepare() {
    const request = ++epoch.current;
    setBusy(true); setStatus('Preparing…');
    try {
      // Recheck source revisions immediately before creating a review record.
      const checked = await aiApi.handoffEligibility(conversation, turn);
      if (epoch.current !== request) return;
      if (!checked.eligible) throw new Error(checked.status);
      const record = await aiApi.prepareHandoff(conversation, turn, action.trim() || 'Review these findings and explain an appropriate engineering correction.');
      if (epoch.current === request) {setHandoff(record); setStatus('Ready to review');}
    } catch (error) {if (epoch.current === request) setStatus(errorText(error));}
    finally {if (epoch.current === request) setBusy(false);}
  }
  async function accept() {
    const request = ++epoch.current;
    setBusy(true);
    try {
      const checked = await aiApi.handoffEligibility(conversation, turn);
      if (epoch.current !== request) return;
      if (!checked.eligible) throw new Error(checked.status);
      const result = await aiApi.acceptHandoff(handoff.id);
      if (epoch.current !== request) return;
      localStorage.setItem('ansibleChat.currentSessionId.v1', result.conversation_id);
      sessionStorage.setItem('ai.engineeringHandoff', JSON.stringify(result));
      window.dispatchEvent(new CustomEvent('cognishield:engineering-handoff', {detail: result}));
      onOpen();
    } catch (error) {if (epoch.current === request) setStatus(errorText(error));}
    finally {if (epoch.current === request) setBusy(false);}
  }
  function cancel() {epoch.current += 1; setOpen(false); setBusy(false);}
  return <><button type="button" className="btn btn-ghost btn-xs mt-2" onClick={() => void review()}><ArrowUpRight size={13}/>Review in Ansible Studio</button>
    {open && <div ref={dialog} onKeyDown={event => {
      if (event.key === 'Escape') {event.stopPropagation(); cancel();}
      if (event.key === 'Tab') {
        const items = [...(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled),textarea:not(:disabled)') || [])];
        const first = items[0], last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last?.focus();}
        else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first?.focus();}
      }
    }} className="absolute inset-2 z-20 rounded-xl border border-base-300 bg-base-100 shadow-xl p-4 overflow-y-auto" role="dialog" aria-modal="true" aria-label="Review engineering handoff">
      <div className="flex justify-between items-center mb-3"><strong>Review in Ansible Studio</strong><button className="btn btn-ghost btn-xs btn-square" aria-label="Cancel engineering handoff" onClick={cancel}><X size={14}/></button></div>
      <p role="status" className="text-sm mb-3">{status}</p>
      {source?.eligible && <><p className="text-sm"><strong>Devices:</strong> {source.device_names.join(', ')}</p>
        {source.scenario && <p className="text-xs text-info mt-2">Development simulation · recorded source revision</p>}
        <ul className="text-xs my-3 space-y-2">{source.evidence.map((item: any, index: number) => <li key={item.id}>Source {index + 1}: {item.source} · {item.origin} · {item.time_scope} · {item.freshness}{item.captured_at ? ' · ' + item.captured_at : ''}</li>)}</ul>
        {!handoff ? <><label className="text-xs block" htmlFor={'handoff-action-' + turn}>Desired follow-up (optional)</label><textarea id={'handoff-action-' + turn} className="textarea textarea-bordered w-full mt-1 text-sm" value={action} onChange={e => setAction(e.target.value)} placeholder="Describe what you want the engineer to review"/><button disabled={busy} className="btn btn-primary btn-sm mt-3" onClick={() => void prepare()}>Prepare review</button></> : <><p className="text-sm my-3">{handoff.requested_action}</p><p className="text-xs opacity-70">Opens a separate Studio conversation with an unsent draft. Send it explicitly to begin engineering.</p><button disabled={busy} className="btn btn-primary btn-sm mt-3" onClick={() => void accept()}>Open unsent draft in Studio</button></>}
      </>}
      <button className="btn btn-ghost btn-sm mt-3 ml-2" onClick={cancel}>Cancel</button>
    </div>}
  </>;
}

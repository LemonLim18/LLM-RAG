import { useEffect, useRef, useState } from 'react';
import AssistantMarkdown from './AssistantMarkdown';
import { X, Send, Plus, Square, RefreshCw, Bot, Sparkles, Database, ChevronRight, MessageSquare, Network, GripHorizontal, Paperclip } from 'lucide-react';
import { aiApi, type AIConversation } from '../src/services/ai';
import { llmApi } from '../src/services/api';

export default function SharedInventoryChat({ onClose, userKey }: { onClose: () => void; userKey: string }) {
  const uploadInput=useRef<HTMLInputElement>(null);
  const [attachments,setAttachments]=useState<{id:string;name:string}[]>([]);
  const [uploading,setUploading]=useState(false);
  const [handoff,setHandoff]=useState<any>(null);
  const [handoffAction,setHandoffAction]=useState('');
  const [showInventory, setShowInventory] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [sessions, setSessions] = useState<AIConversation[]>([]);
  const [session, setSession] = useState<AIConversation | null>(null);
  const [prompt, setPrompt] = useState('');
  const [models, setModels] = useState<string[]>([]);
  const [model, setModel] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const active = useRef<{ controller: AbortController; session: string; request: string } | null>(null);
  const epoch = useRef(0);
  const [position, setPosition] = useState({ x: Math.max(0, window.innerWidth - 460), y: 80 });
  const drag = useRef<{ x: number; y: number } | null>(null);
  const refresh = async () => {
    const captured = epoch.current;
    const errors: string[] = [];
    try {
      const inventory = await aiApi.inventory();
      if (captured !== epoch.current) return;
      setDevices(inventory.data.devices);
    } catch (e) { errors.push('Inventory: ' + String(e)); }
    if (captured !== epoch.current) return;
    try {
      const result = await aiApi.list('floating');
      if (captured !== epoch.current) return;
      const saved = localStorage.getItem(`ai.floating.${userKey}`);
      const current = result.sessions.find(s => s.id === saved) || result.sessions[0] || await aiApi.create('floating');
      if (captured !== epoch.current) return;
      setSessions(result.sessions); setSession(current);
      localStorage.setItem(`ai.floating.${userKey}`,current.id);
    } catch (e) { errors.push('Conversations: ' + String(e)); }
    if (captured !== epoch.current) return;
    try {
      const runtime = await llmApi.getRuntime();
      if (captured !== epoch.current) return;
      const local = runtime.providers.find(p => p.name === 'ollama');
      setModels(local?.models || []); setModel(current => local?.models.includes(current) ? current : runtime.active_model || '');
      if (!local?.available) errors.push(local?.error || 'Local inference is unavailable. Inventory remains available.');
    } catch (e) { errors.push('Model availability: ' + String(e)); }
    if (captured === epoch.current) setError(errors.join('\n'));
  };
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [session?.messages.length, busy]);
  useEffect(() => {
    const clamp = () => setPosition(p => ({ x: Math.max(8, Math.min(window.innerWidth - Math.min(440, window.innerWidth - 16) - 8, p.x)), y: Math.max(8, Math.min(window.innerHeight - 180, p.y)) }));
    window.addEventListener('resize', clamp); return () => window.removeEventListener('resize', clamp);
  }, []);
  const select = (value: AIConversation) => { epoch.current++; stop(); setAttachments([]); setHandoff(null); setHandoffAction(''); setSession(value); localStorage.setItem(`ai.floating.${userKey}`, value.id); };
  const stop = () => { const request = active.current; if (request) { request.controller.abort(); void aiApi.cancel(request.session, request.request).catch(() => {}); active.current = null; } setBusy(false); };
  useEffect(() => {
    void refresh();
    return () => { epoch.current++; const current = active.current; if (current) { current.controller.abort(); void aiApi.cancel(current.session, current.request).catch(() => {}); } };
  }, [userKey]);
  const send = async () => {
    if (!session || (!prompt.trim() && !attachments.length) || busy || uploading) return;
    const captured = epoch.current;
    const text = prompt.trim() || 'Explain the attached files.'; setPrompt(''); setBusy(true); setError('');
    const request = { controller: new AbortController(), session: session.id, request: crypto.randomUUID() };
    active.current = request;
    setSession(s => s ? { ...s, messages: [...s.messages, { id: request.request, role: 'user', content: text, timestamp: Date.now() }] } : s);
    try {
      await aiApi.turn(session.id, { request_id: request.request, prompt: text, model: model || undefined, attachment_ids:attachments.map(a=>a.id) }, request.controller.signal);
      const updated = await aiApi.get(session.id);
      if (captured === epoch.current) { setSession(updated); setAttachments([]); setSessions(prev => [updated, ...prev.filter(s => s.id !== updated.id)]); }
    } catch (e) { if (!request.controller.signal.aborted && captured === epoch.current) setError(e instanceof Error ? e.message : String(e)); }
    finally { if (active.current === request) { active.current = null; setBusy(false); } }
  };
  return <section role="dialog" aria-label="AI Assistant" className="assistant-surface fixed z-50 bg-base-100 border border-base-300 rounded-2xl shadow-2xl flex flex-col overflow-hidden" style={{ left: position.x, top: position.y, width: 'min(440px, calc(100vw - 16px))', height: 'min(700px, calc(100dvh - 96px))' }}>
    <header className="flex items-center gap-3 px-4 py-3 border-b border-base-300 touch-none cursor-move bg-base-200/60" onPointerDown={e => { if ((e.target as HTMLElement).closest('button,select')) return; drag.current = { x: e.clientX - position.x, y: e.clientY - position.y }; e.currentTarget.setPointerCapture(e.pointerId); }} onPointerMove={e => { if (drag.current) setPosition({ x: Math.max(8, Math.min(window.innerWidth - Math.min(440, window.innerWidth - 16) - 8, e.clientX - drag.current.x)), y: Math.max(8, Math.min(window.innerHeight - 180, e.clientY - drag.current.y)) }); }} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
      <span className="rounded-xl bg-primary/15 text-primary p-2"><Bot size={20} /></span><div className="grow"><h2 className="font-semibold text-sm">AI Assistant</h2><p className="text-[11px] text-base-content/50">Network operations · Local</p></div><GripHorizontal size={16} className="opacity-25" />
      <button aria-label="New conversation" title="New conversation" className="btn btn-ghost btn-xs btn-square" onClick={() => void aiApi.create('floating').then(value => { select(value); setSessions(s => [value, ...s]); }).catch(e => setError(String(e)))}><Plus size={16} /></button>
      <button aria-label="Close AI Assistant" className="btn btn-ghost btn-xs btn-square" onClick={onClose}><X size={16} /></button>
    </header>
    <div className="flex items-center gap-2 px-4 py-2 border-b border-base-300/60"><MessageSquare size={13} className="opacity-40" /><select aria-label="Assistant conversation" className="select select-ghost select-xs flex-1 min-w-0 text-base-content/70" value={session?.id || ''} onChange={e => { const value = sessions.find(s => s.id === e.target.value); if (value) select(value); }}>{session && !sessions.some(s => s.id === session.id) && <option value={session.id}>{session.title || 'New conversation'}</option>}{sessions.map(s => <option key={s.id} value={s.id}>{s.title || 'New conversation'}</option>)}</select><button aria-label="Refresh assistant" disabled={busy} className="btn btn-xs btn-ghost btn-square" onClick={() => void refresh()}><RefreshCw size={13} /></button></div>
    <div className="grow min-h-0 overflow-y-auto px-4 py-4 space-y-5">
      {!session?.messages.length && <div className="py-5"><span className="inline-flex p-3 rounded-2xl bg-primary/10 text-primary mb-4"><Sparkles size={24} /></span><h3 className="text-xl font-semibold tracking-tight mb-2">How can I help?</h3><p className="text-sm leading-relaxed text-base-content/60 mb-5">Ask about inventory, topology, metrics, logs or configurations—or work through a general question.</p><div className="space-y-2">{[{icon:Database,text:'What devices are in my network?'},{icon:Network,text:'Explain the difference between OSPF and BGP'},{icon:MessageSquare,text:'Investigate network alerts, logs and telemetry'}].map(({icon:Icon,text}) => <button key={text} className="w-full flex items-center gap-3 rounded-xl border border-base-300 px-3 py-3 text-left text-xs hover:border-primary/40 hover:bg-primary/5 transition-colors" onClick={() => setPrompt(text)}><Icon size={16} className="text-primary shrink-0" /><span className="grow">{text}</span><ChevronRight size={13} className="opacity-40" /></button>)}</div></div>}
      {session?.messages.filter(m => m.role !== 'system').map(m => <article key={m.id} className={m.role === 'user' ? 'ml-7 bg-base-200 rounded-2xl px-3.5 py-3' : ''}><div className="flex items-center gap-2 mb-2 text-[11px] font-semibold text-base-content/55">{m.role !== 'user' && <Bot size={14} className="text-primary" />}{m.role === 'user' ? 'You' : 'AI Assistant'}</div><AssistantMarkdown content={m.content} />{!!m.evidence?.length && <details className="mt-3 text-[11px] text-base-content/50"><summary className="cursor-pointer">{m.evidence.length} sources</summary>{m.evidence.map((e,index) => <p key={e.id} className="mt-1 break-all">S{index+1} · {e.source} · {e.origin}</p>)}</details>}</article>)}
      {busy && <div role="status" className="flex items-center gap-2 text-xs text-base-content/60"><span className="loading loading-dots loading-sm text-primary" />Thinking through your request…</div>}
      {error && <div role="status" className="rounded-lg border border-error/20 bg-error/5 p-3 text-xs leading-relaxed">{error}</div>}<div ref={bottom} />
    </div>
    {session?.messages.some(m=>m.role==='assistant') && <div className="px-4 py-2 border-t border-base-300">
      {!handoff ? <details><summary className="text-xs cursor-pointer">Prepare engineering handoff</summary><textarea aria-label="Requested engineering action" className="textarea textarea-bordered w-full mt-2 text-xs" placeholder="Describe the action to review in Ansible Studio" value={handoffAction} onChange={e=>setHandoffAction(e.target.value)}/><button className="btn btn-xs mt-2" disabled={busy || !handoffAction.trim()} onClick={()=>{const last=[...session.messages].reverse().find(m=>m.role==='assistant');if(last)void aiApi.prepareHandoff(session.id,last.id,handoffAction).then(setHandoff).catch(e=>setError(String(e)));}}>Review handoff</button></details> : <div className="text-xs space-y-2"><strong>Review engineering handoff</strong><p>{handoff.requested_action}</p><p>{handoff.device_refs.length} device references · {handoff.evidence.length} evidence records</p><p className="opacity-60">Opens a separate Studio conversation. Send the draft request explicitly to begin engineering.</p><button className="btn btn-primary btn-xs" onClick={()=>void aiApi.acceptHandoff(handoff.id).then(result=>{localStorage.setItem('ansibleChat.currentSessionId.v1',result.conversation_id);sessionStorage.setItem('ai.engineeringHandoff',JSON.stringify(result));window.dispatchEvent(new CustomEvent('cognishield:engineering-handoff',{detail:result}));onClose();}).catch(e=>setError(String(e)))}>Open in Studio</button><button className="btn btn-ghost btn-xs" onClick={()=>setHandoff(null)}>Cancel</button></div>}
    </div>}
    <div className="border-t border-base-300/70 px-4 py-2"><button aria-expanded={showInventory} className="flex items-center gap-2 w-full text-[11px] text-base-content/60 py-1" onClick={() => setShowInventory(v => !v)}><Database size={13} /><span>Network context</span><span className="ml-auto">{devices.length} stored devices</span><ChevronRight size={12} className={showInventory ? 'rotate-90' : ''} /></button>{showInventory && <div className="max-h-44 overflow-y-auto py-2"><p className="text-[11px] opacity-50 mb-2">Stored inventory · Reachability not measured</p>{devices.map(d => <details key={d.id} className="rounded-lg bg-base-200 p-2 mb-1 text-xs"><summary className="cursor-pointer">{d.hostname} · {d.vendor || 'Unknown vendor'}</summary><p className="my-1 opacity-60">{d.management_ip || 'No management address'} · {d.role}</p>{d.interfaces?.map((i: any) => <p key={i.id} className="opacity-60">{i.name} {i.ip_address}</p>)}</details>)}{!devices.length && <p className="text-xs opacity-60">No devices stored.</p>}</div>}</div>
    <input ref={uploadInput} type="file" multiple className="hidden" accept=".yaml,.yml,.j2,.cfg,.conf,.txt,.json,.log,.py,.pdf,.png,.jpg,.jpeg,.webp,.jinja,.jinja2" onChange={e=>{const files=Array.from(e.target.files || []);e.target.value='';if(!session)return;const current=session.id;setUploading(true);void (async()=>{try{if(files.length+attachments.length>5)throw new Error('Attach at most five files per request.');const added:{id:string;name:string}[]=[];for(const file of files)added.push(await aiApi.upload(current,file));if(localStorage.getItem(`ai.floating.${userKey}`)===current)setAttachments(prev=>[...prev,...added]);}catch(err){setError(String(err));}finally{setUploading(false);}})();}}/>
    <div className="px-3 pb-3">{!!attachments.length && <div className="flex flex-wrap gap-1 py-2">{attachments.map(a=><span key={a.id} className="badge badge-outline text-xs gap-1">{a.name}<button aria-label={'Remove '+a.name} onClick={()=>{if(session)void aiApi.removeAttachment(session.id,a.id);setAttachments(prev=>prev.filter(file=>file.id!==a.id));}}><X size={11}/></button></span>)}</div>}<div className="border border-base-300 rounded-xl bg-base-200/40 focus-within:border-primary/50 overflow-hidden"><textarea aria-label="Message AI Assistant" placeholder="Ask anything about your network…" className="block w-full bg-transparent resize-none outline-none px-3 pt-3 pb-2 text-sm min-h-20" rows={2} value={prompt} onChange={e => setPrompt(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} /><div className="flex items-center px-2 pb-2 gap-2"><button className="btn btn-ghost btn-xs btn-square" aria-label="Attach file to AI Assistant" disabled={uploading || busy || !session} onClick={()=>uploadInput.current?.click()}><Paperclip size={14}/></button><select aria-label="Assistant model" className="select select-ghost select-xs max-w-64 text-base-content/55" value={model} onChange={e => setModel(e.target.value)}>{!models.length && <option value="">Ollama unavailable</option>}{models.map(m => <option key={m}>{m}</option>)}</select>{busy ? <button aria-label="Stop response" className="btn btn-sm btn-square ml-auto" onClick={stop}><Square size={14} /></button> : <button aria-label="Send message" className="btn btn-primary btn-sm btn-square ml-auto rounded-lg" disabled={(!prompt.trim() && !attachments.length) || !session || !model || uploading} onClick={() => void send()}><Send size={15} /></button>}</div></div><p className="text-[10px] text-center text-base-content/35 mt-2">Enter to send · Shift+Enter for a new line</p></div>
  </section>;
}

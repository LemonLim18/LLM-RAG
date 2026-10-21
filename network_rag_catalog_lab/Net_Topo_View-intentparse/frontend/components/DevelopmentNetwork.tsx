import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import Editor from '@monaco-editor/react';
import { request } from '../src/services/api';
import { useMonacoTheme } from '../src/utils/monacoTheme';
import ScenarioWorkbench from './ScenarioWorkbench';

/** Server configuration enables authority; this UI cannot enable it or grant tools. */
export default function DevelopmentNetwork({isAdmin}:{isAdmin:boolean}) {
  const [state,setState]=useState<any>(null);
  const [open,setOpen]=useState(false);
  const [workbench,setWorkbench]=useState(false);
  const [text,setText]=useState('');
  const [selected,setSelected]=useState('');
  const [copyId,setCopyId]=useState('');
  const [interfaceId,setInterfaceId]=useState('');
  const [adminState,setAdminState]=useState('down');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const {themeName:theme}=useMonacoTheme();
  const install=(value:any)=>{setState(value);setText(JSON.stringify(value.scenario,null,2));setSelected(value.context?.id || '');};
  const reload=async()=>{try{install(await request<any>('/development-network'));setError('');}catch(e){setError(String(e));}};
  useEffect(()=>{
    void reload();
    const changed=()=>{void reload();};
    window.addEventListener('cognishield:scenario-changed',changed);
    return ()=>window.removeEventListener('cognishield:scenario-changed',changed);
  },[]);
  async function change(action:string,definition?:any,scenario_id?:string) {
    setBusy(true);setError('');
    try {
      install(await request('/development-network',{method:'PUT',body:JSON.stringify({action,expected_revision:state.context.source_revision,definition,scenario_id})}));
      window.dispatchEvent(new Event('cognishield:scenario-changed'));
    } catch(e){setError(e instanceof Error ? e.message : String(e));}finally{setBusy(false);}
  }
  async function save(action='edit') {
    try {const definition=JSON.parse(text);if(action==='duplicate')definition.id=copyId;await change(action,definition);}
    catch(e){setError('Invalid JSON: '+String(e));}
  }
  async function event() {
    setBusy(true);setError('');
    try {install(await request('/development-network/interface-event',{method:'POST',body:JSON.stringify({expected_revision:state.context.source_revision,interface_id:Number(interfaceId),admin_status:adminState})}));window.dispatchEvent(new Event('cognishield:scenario-changed'));}
    catch(e){setError(e instanceof Error ? e.message : String(e));}finally{setBusy(false);}
  }
  function exportScenario(){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(state.scenario,null,2)],{type:'application/json'}));a.download=state.scenario.id+'.json';a.click();URL.revokeObjectURL(a.href);}
  if(!state)return null;
  return <>
    <div className={'px-4 py-1 text-xs border-b border-base-300 flex items-center gap-3 '+(state.enabled?'bg-info/10':'bg-base-100')}>
      <span>{state.enabled?`SIMULATED DATA · ${state.context.id} · revision ${state.context.revision} · ${state.context.logical_time}`:'Development network disabled'}</span>
      {isAdmin && <button className="btn btn-ghost btn-xs" onClick={()=>{setOpen(true);void reload();}}>Development scenarios</button>}
      {isAdmin && <button className="btn btn-ghost btn-xs" onClick={()=>setWorkbench(true)}>Scenario Workbench</button>}
    </div>
    {workbench&&<ScenarioWorkbench onClose={()=>{setWorkbench(false);void reload();}}/>}
    {open && createPortal(<div className="fixed inset-0 z-[90] bg-black/60 p-5 flex items-center justify-center"><section role="dialog" aria-label="Development Network" className="bg-base-100 rounded-xl border border-base-300 shadow-xl w-full max-w-6xl max-h-[94vh] overflow-auto p-5 space-y-3">
      <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Development Network</h2><button className="btn btn-ghost btn-sm" onClick={()=>setOpen(false)}>Close development scenarios</button></div>
      <p className="text-sm opacity-70">Selected scenario is authoritative only for this development simulation. No physical device operations occur. Scenario edits do not change ordinary inventory or published V9 knowledge.</p>
      {!state.enabled?<p>{state.message}</p>:<>
        <div className="flex flex-wrap items-center gap-2">
          <select aria-label="Development scenario" className="select select-bordered select-sm" value={selected} onChange={e=>setSelected(e.target.value)} disabled={busy}>{state.catalog.map((s:any)=><option key={s.id} value={s.id}>{s.id} · {s.title}</option>)}</select>
          <button className="btn btn-sm" disabled={busy} onClick={()=>void change('select',undefined,selected)}>Select scenario</button>
          <button className="btn btn-sm btn-outline" disabled={busy} onClick={()=>void change('reset',undefined,selected)}>Reset selected scenario</button>
          <button className="btn btn-sm btn-outline" onClick={exportScenario}>Export scenario JSON</button>
          <label className="btn btn-sm btn-outline">Import scenario JSON<input aria-label="Import scenario JSON" type="file" accept=".json" className="hidden" disabled={busy} onChange={async e=>{const f=e.target.files?.[0];if(!f)return;if(f.size>2000000){setError('Scenario exceeds 2 MB');return;}try{await change('import',JSON.parse(await f.text()));}catch(e){setError(String(e));}}}/></label>
        </div>
        <p className="text-xs opacity-70">Logical time: {state.context.logical_time} · Model scope: {state.context.model_scope}. Reload after revision conflicts; saving requires the revision you inspected.</p>
        <Editor height="45vh" language="json" theme={theme} value={text} onChange={v=>setText(v || '')} options={{editContext:false,readOnly:busy,minimap:{enabled:false},fontSize:13,automaticLayout:true}} />
        <div className="flex flex-wrap items-center gap-2"><button className="btn btn-primary btn-sm" disabled={busy} onClick={()=>void save()}>Validate & save scenario</button><button className="btn btn-sm" disabled={busy} onClick={()=>void reload()}>Reload scenario</button><input aria-label="Duplicate scenario ID" className="input input-bordered input-sm" placeholder="NEW-SCENARIO-001" value={copyId} onChange={e=>setCopyId(e.target.value)}/><button className="btn btn-sm" disabled={busy || !copyId} onClick={()=>void save('duplicate')}>Duplicate scenario</button></div>
        <details className="border border-base-300 rounded p-3"><summary>Model an administrative interface event</summary><p className="text-xs opacity-60 py-2">Atomically updates interface state, the modeled running configuration, dependent link/probe observations, counters and event history. Enabling an interface leaves operational recovery unknown until new observations.</p><div className="flex flex-wrap gap-2"><select aria-label="Scenario interface" className="select select-bordered select-sm" value={interfaceId} onChange={e=>setInterfaceId(e.target.value)}><option value="">Choose interface</option>{state.scenario.interfaces.map((i:any)=><option key={i.id} value={i.id}>{state.scenario.devices.find((d:any)=>d.id===i.device_id)?.hostname} · {i.name}</option>)}</select><select aria-label="Scenario administrative state" className="select select-bordered select-sm" value={adminState} onChange={e=>setAdminState(e.target.value)}><option value="down">down</option><option value="up">up</option></select><button className="btn btn-sm" disabled={busy || !interfaceId} onClick={()=>void event()}>Apply simulated event</button></div></details>
      </>}
      {error && <p role="alert" className="text-error whitespace-pre-wrap text-sm">{error}</p>}
    </section></div>,document.body)}
  </>;
}

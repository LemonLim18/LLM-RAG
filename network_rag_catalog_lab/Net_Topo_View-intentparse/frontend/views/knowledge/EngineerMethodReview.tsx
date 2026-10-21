import {useEffect,useState} from 'react';
import {knowledgeApi} from '../../src/services/api';
import AssistantMarkdown from '../../components/AssistantMarkdown';
import {Btn,FormField} from './KnowledgeLayouts';

/** Optional inspection; Publish/Activate is the authenticated engineer decision. */
export default function EngineerMethodReview({revision}:{revision:string}) {
  const [report,setReport]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [expanded,setExpanded]=useState<string|null>(null);
  const [search,setSearch]=useState(''),[vendor,setVendor]=useState(''),[status,setStatus]=useState('');
  const load=async()=>{setBusy(true);setError('');try{setReport((await knowledgeApi.reviews(true)).data);setExpanded(null)}catch(e:any){setError(e.message)}finally{setBusy(false)}};
  useEffect(()=>{void load()},[revision]);
  const rows:any[]=report?.rows||[];
  const visible=rows.filter(r=>(!vendor||r.binding.vendor===vendor)&&(!status||(status==='approved'?r.approved:!r.approved))&&(!search||[r.binding.operation_id,r.binding.platform,...r.binding.versions].join(' ').toLowerCase().includes(search.toLowerCase().trim())));
  return <section className="kr-panel kr-method-review" aria-label="Template rendering checks" aria-busy={busy}>
    <header className="kr-panel-head"><h2>Template rendering checks</h2><Btn disabled={busy} onClick={()=>void load()}>{busy?'Checking methods…':'Refresh checks'}</Btn></header>
    <div className="p-4 space-y-3">
      <p>Publish Release validates and activates the pack as your authenticated engineer account. There is no separate sign-off step. Vendor/device certification is optional information; publication does not deploy configurations.</p>
      <p>Checks cover the supplied rendering fixtures, schema negatives and declared profiles. They do not certify every command, conditional branch or device behavior.</p>
      <p><strong>{rows.filter(r=>r.checks?.status==='PASS').length} rendering checks passed</strong> / {report?.counts?.bindings??0} authored bindings. Publication actions are recorded in the audit history.</p>
      {error&&<p role="alert" className="text-error">{error}</p>}
      <div className="kr-method-filters"><FormField label="Find methods"><input aria-label="Find review methods" placeholder="Operation, platform or version" value={search} onChange={e=>setSearch(e.target.value)}/></FormField><FormField label="Vendor"><select aria-label="Filter review vendor" value={vendor} onChange={e=>setVendor(e.target.value)}><option value="">All vendors</option>{[...new Set(rows.map(r=>r.binding.vendor as string))].sort().map(v=><option key={v} value={v}>{v}</option>)}</select></FormField><FormField label="Publication"><select aria-label="Filter review publication" value={status} onChange={e=>setStatus(e.target.value)}><option value="">All methods</option><option value="pending">No publication record</option><option value="approved">Publication recorded</option></select></FormField></div>
      <div className="kr-method-actions"><Btn disabled={busy||!report} onClick={()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='cognishield-native-method-review.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}}>Download exact review bundle</Btn>
      <span aria-live="polite">{visible.length} methods shown</span></div>
      <div className="overflow-auto max-h-[32rem]"><table><thead><tr><th>Operation / scope</th><th>Fixture checks</th><th>Publication / certification</th><th>Review</th></tr></thead><tbody>
        {visible.map(r=><tr key={r.identity}>

          <td><strong>{r.binding.operation_id}</strong><br/>{r.binding.vendor} · {r.binding.platform} · {r.binding.versions.join(', ')}</td>
          <td><span className={'kl-pill '+(r.checks?.status==='PASS'?'teal':'pink')}>{r.checks?.status||'NOT RUN'}</span>{r.checks?.errors?.map((e:string)=><p key={e}>{e}</p>)}</td>
          <td>{r.approved?'Engineer publication recorded':r.checks?.status==='PASS'?'Draft — rendering checks passed':'Draft — run structural checks'}<br/><small>Vendor semantics: {r.certifications.vendor_semantics}; device: {r.certifications.device}; Ansible: {r.certifications.ansible}</small>{r.approval&&<p>{r.approval.approved_by} · {r.approval.approved_at}</p>}</td>
          <td><Btn onClick={()=>setExpanded(expanded===r.identity?null:r.identity)}>Inspect method</Btn></td>
        </tr>)}
        {visible.length===0&&<tr><td colSpan={4}>No methods match these filters.</td></tr>}
      </tbody></table></div>
      {expanded&&(()=>{const r=rows.find(x=>x.identity===expanded);return <div className="border rounded p-3 space-y-2"><h3>{r.identity}</h3><p>Review fingerprint <code className="break-all">{r.fingerprint}</code></p><p>Template SHA-256 <code className="break-all">{r.template_sha256}</code></p><AssistantMarkdown content={'```jinja2\n'+r.template_content+'\n```'}/><details><summary>Contract, assumptions, limitations, risks and exact fixtures</summary><pre className="overflow-auto max-h-96">{JSON.stringify({schema:r.schema,method:r.method,checks:r.checks},null,2)}</pre></details></div>})()}

    </div>
  </section>;
}

import { useEffect, useState } from 'react';
import { aiApi } from '../src/services/ai';
import { useCapability } from '../src/localLab';

export default function InventoryMetadataEditor({ deviceId }: { deviceId: number }) {
  const [site, setSite] = useState(''); const [location, setLocation] = useState(''); const [aliases, setAliases] = useState('');
  const [status, setStatus] = useState(''); const [busy, setBusy] = useState(true);
  const [facts, setFacts] = useState('{}'); const [factsRevision, setFactsRevision] = useState('');
  const writable = useCapability('inventory.write');
  useEffect(() => { let active = true; setBusy(true); void aiApi.inventory().then(r => { const d = r.data.devices.find(d => d.id === deviceId); if (active && d) { setSite(d.site); setLocation(d.location); setAliases(d.aliases.join(', ')); setFacts(JSON.stringify(d.engineering_facts || {},null,2)); setFactsRevision(d.engineering_facts_revision); setStatus(''); } }).catch(e => { if (active) setStatus(String(e)); }).finally(() => { if (active) setBusy(false); }); return () => { active = false; }; }, [deviceId]);
  return <fieldset className="border border-base-300 rounded-lg p-3 space-y-2" disabled={busy || !writable}>
    <legend className="text-sm">Engineering inventory references</legend>
    <label className="form-control text-xs">Site<input className="input input-bordered input-sm" maxLength={100} value={site} onChange={e => setSite(e.target.value)} /></label>
    <label className="form-control text-xs">Location<input className="input input-bordered input-sm" maxLength={200} value={location} onChange={e => setLocation(e.target.value)} /></label>
    <label className="form-control text-xs">Aliases (comma separated)<input className="input input-bordered input-sm" value={aliases} onChange={e => setAliases(e.target.value)} /></label>
    <button className="btn btn-sm" onClick={() => { setBusy(true); void aiApi.saveInventoryMetadata(deviceId, { site, location, aliases: aliases.split(',').map(s => s.trim()).filter(Boolean) }).then(() => setStatus('Inventory references saved.')).catch(e => setStatus(e instanceof Error ? e.message : String(e))).finally(() => setBusy(false)); }}>Save inventory references</button>
    <details><summary className="text-sm cursor-pointer">Recorded engineering facts</summary>
      <p className="text-xs my-2">Source-referenced planned or sample facts for V9 compatibility checks. These records do not establish live device state. Identity and interfaces remain bound to SQLite inventory.</p>
      <label className="form-control text-xs">Engineering facts (JSON)<textarea aria-label="Engineering facts JSON" className="textarea textarea-bordered font-mono text-xs h-60" maxLength={100000} value={facts} onChange={e => setFacts(e.target.value)} /></label>
      <button className="btn btn-sm mt-2" onClick={async () => { setBusy(true); try { const result=await aiApi.saveEngineeringFacts(deviceId,JSON.parse(facts),factsRevision); setFactsRevision(result.revision); setStatus('Engineering facts saved with source references. No device action occurred.'); } catch(e) { setStatus(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); } }}>Save engineering facts</button>
    </details>
    {status && <p role="status" className="text-xs">{status}</p>}
  </fieldset>;
}

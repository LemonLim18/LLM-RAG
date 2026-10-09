import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useWorkbench } from '../../app/workbenchContext';
import { registerDevice, RegistrationError, type DeviceRegistration } from '../../services/inventoryApi';

const platforms: Record<string, string> = { cisco: 'iosxe', huawei: 'vrp', juniper: 'junos' };
const features = ['interface', 'vlan', 'ip_address', 'static_routing', 'ospf', 'bgp', 'isis', 'acl', 'qos'];
const list = (text: string) => text.split(',').map((value) => value.trim()).filter(Boolean);
type InterfaceEntry = DeviceRegistration['device']['interfaces'][number];

export function AddDeviceForm({ onClose, onRegistered }: { onClose: () => void; onRegistered: () => void }) {
  const { state, refreshInventory, localPlanning } = useWorkbench();
  const dialog = useRef<HTMLDialogElement>(null);
  const submitting = useRef(false);
  const [pending, setPending] = useState(false);
  const [revision, setRevision] = useState(state.inventory.revision ?? '');
  const [fields, setFields] = useState({ hostname: '', display_name: '', kind: 'router', vendor: 'cisco', version: '', site: '', role: '', location: '', aliases: '', tags: '' });
  const [declared, setDeclared] = useState<string[]>([]);
  const [interfaces, setInterfaces] = useState<InterfaceEntry[]>([]);
  const [error, setError] = useState('');
  const [needsReload, setNeedsReload] = useState(false);
  const [registeredId, setRegisteredId] = useState('');
  const [notice, setNotice] = useState('');
  useEffect(() => { dialog.current?.showModal(); }, []);

  const reload = async () => {
    if (submitting.current) return;
    submitting.current = true; setPending(true);
    try {
      const snapshot = await refreshInventory(registeredId || undefined);
      if (snapshot.inventory_revision !== revision) localPlanning.noteInventoryChange();
      setRevision(snapshot.inventory_revision); setNeedsReload(false); setError('');
      setNotice('Inventory reloaded. Review the device list and form before submitting.');
      if (registeredId) { onRegistered(); onClose(); }
    } catch { setError('Inventory reload failed. Existing workspace state was retained.'); }
    finally { submitting.current = false; setPending(false); }
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting.current || needsReload || registeredId) return;
    if (!declared.length) { setError('Select at least one explicitly declared capability. No capability is assumed.'); return; }
    if (Object.entries(fields).some(([key, value]) => !['aliases', 'tags', 'location'].includes(key) && !value.trim())) {
      setError('Complete all required device fields.'); return;
    }
    submitting.current = true; setPending(true); setError(''); setNotice('');
    try {
      const result = await registerDevice({ expected_inventory_revision: revision, device: {
        ...fields, hostname: fields.hostname.trim(), platform: platforms[fields.vendor], location: fields.location.trim() || null,
        aliases: list(fields.aliases), tags: list(fields.tags), capabilities: { features: declared },
        interfaces: interfaces.map((item) => ({ ...item, aliases: item.aliases.map((alias) => alias.trim()).filter(Boolean) })),
      } });
      setRegisteredId(result.device.id);
      localPlanning.noteInventoryChange();
      setNotice(`Registered ${result.device.hostname}. Reloading shared inventory…`);
      try {
        await refreshInventory(result.device.id);
        onRegistered(); onClose();
      } catch {
        setNeedsReload(true);
        setError('Registration succeeded, but inventory reload failed. Reload only; do not submit the device again.');
      }
    } catch (caught) {
      const registrationError = caught instanceof RegistrationError ? caught : new RegistrationError('OUTCOME_UNKNOWN', 'Registration outcome unknown. Reload inventory before submitting again.');
      setError(`${registrationError.code}: ${registrationError.message}`);
      setNeedsReload(['STALE_INVENTORY', 'OUTCOME_UNKNOWN', 'INVENTORY_STORAGE_UNAVAILABLE', 'INVALID_REGISTRATION'].includes(registrationError.code));
    } finally { submitting.current = false; setPending(false); }
  };
  const updateInterface = (index: number, change: Partial<InterfaceEntry>) => setInterfaces((prior) => prior.map((item, i) => i === index ? { ...item, ...change } : item));
  return <dialog className="registration-dialog" ref={dialog} aria-labelledby="registration-title"
    onCancel={(event) => { if (pending) event.preventDefault(); else onClose(); }}>
    <form onSubmit={(event) => { void submit(event); }} aria-label="Register synthetic device">
      <header><div><span className="eyebrow">Shared V9 inventory · synthetic only</span><h2 id="registration-title">Add Device</h2></div>
        <button type="button" disabled={pending} onClick={onClose} aria-label="Close registration">Close</button></header>
      <p>No connection, discovery or deployment. Capabilities are declarations, not validation of supported operations.</p>
      <details><summary>Expected inventory revision</summary><code className="registration-revision">{revision}</code></details>
      <fieldset disabled={pending || Boolean(registeredId)}>
        <legend>Device identity and context</legend>
        <div className="registration-grid">
          {(['hostname', 'display_name', 'version', 'site', 'role', 'location', 'aliases', 'tags'] as const).map((key) => {
            const label = { hostname: 'Hostname', display_name: 'Display name', version: 'Software version', site: 'Site', role: 'Role', location: 'Location (optional)', aliases: 'Device aliases (comma separated)', tags: 'Tags (comma separated)' }[key];
            return <label key={key}>{label}<input value={fields[key]} maxLength={key === 'aliases' || key === 'tags' ? 1000 : 120}
              required={!['location', 'aliases', 'tags'].includes(key)} autoFocus={key === 'hostname'}
              onChange={(event) => setFields({ ...fields, [key]: event.target.value })} /></label>;
          })}
          <label>Device kind<select value={fields.kind} onChange={(event) => setFields({ ...fields, kind: event.target.value })}>
            <option value="router">Router</option><option value="switch">Switch</option><option value="firewall">Firewall</option></select></label>
          <label>Vendor / platform<select value={fields.vendor} onChange={(event) => setFields({ ...fields, vendor: event.target.value })}>
            <option value="cisco">Cisco / iosxe</option><option value="huawei">Huawei / vrp</option><option value="juniper">Juniper / junos</option></select></label>
        </div>
        <fieldset><legend>Declared capabilities (select at least one)</legend><div className="registration-features">
          {features.map((feature) => <label key={feature}><input type="checkbox" checked={declared.includes(feature)} onChange={(event) => setDeclared(event.target.checked ? [...declared, feature] : declared.filter((value) => value !== feature))} />{feature}</label>)}
        </div></fieldset>
        <fieldset><legend>Initial interfaces (optional, saved with this device)</legend>
          <p>Enter actual synthetic names and aliases. Management is a descriptive role only; no address or link is assumed.</p>
          {interfaces.map((item, index) => <div className="registration-interface" key={index}>
            <label>Interface {index + 1} name<input required value={item.name} onChange={(event) => updateInterface(index, { name: event.target.value })} /></label>
            <label>Interface {index + 1} aliases<input value={item.aliases.join(',')} onChange={(event) => updateInterface(index, { aliases: event.target.value.split(',') })} /></label>
            <label>Interface {index + 1} type<select value={item.type} onChange={(event) => updateInterface(index, { type: event.target.value })}><option value="ethernet">Ethernet</option><option value="loopback">Loopback</option></select></label>
            <label>Interface {index + 1} role<input required value={item.role} placeholder="e.g. uplink or management" onChange={(event) => updateInterface(index, { role: event.target.value })} /></label>
            <label><input type="checkbox" checked={item.enabled} onChange={(event) => updateInterface(index, { enabled: event.target.checked })} />Interface {index + 1} administratively enabled</label>
            <button type="button" onClick={() => setInterfaces(interfaces.filter((_, i) => i !== index))}>Remove initial interface {index + 1}</button>
          </div>)}
          <button type="button" disabled={interfaces.length >= 64} onClick={() => setInterfaces([...interfaces, { name: '', aliases: [], type: 'ethernet', role: '', enabled: false }])}>Add initial interface</button>
        </fieldset>
      </fieldset>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <p>Existing V9 sessions are not refreshed. Inventory changes can make their next answer fail the source-revision check.</p>
      <footer><button type="button" disabled={pending} onClick={() => { void reload(); }}>Reload inventory revision</button>
        <button type="submit" disabled={pending || needsReload || Boolean(registeredId) || !revision}>{pending ? 'Saving / loading…' : 'Register synthetic device'}</button></footer>
    </form>
  </dialog>;
}

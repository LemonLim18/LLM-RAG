import { AlertTriangle, ChevronDown, LoaderCircle, Network, RefreshCw, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useWorkbench } from '../../app/workbenchContext';
import { RouterIcon } from '../../components/icons/RouterIcon';

const vendorLabels: Record<string, string> = { cisco: 'Cisco', huawei: 'Huawei', juniper: 'Juniper' };
const vendorLabel = (vendor: string) => vendorLabels[vendor] ?? vendor;
const titleCase = (value: string) => value.replace(/(^|[_-])\w/g, (match) => match.replace(/[_-]/, ' ').toUpperCase());

export function ExplorerPanel() {
  const { state, dispatch, retryInventory } = useWorkbench();
  const [query, setQuery] = useState('');
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return state.devices;
    return state.devices.filter((device) => [device.hostname, device.display_name, device.vendor, device.site, device.role, device.location ?? '', ...device.tags].some((value) => value.toLowerCase().includes(needle)));
  }, [query, state.devices]);

  return (
    <aside className="panel explorer-panel" aria-label="Infrastructure explorer">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Infrastructure</span>
          <h2>Explorer</h2>
        </div>
        <span className="count-badge" aria-label={`${state.devices.length} demo inventory devices`}>{state.devices.length}</span>
      </div>
      <div className="demo-callout demo-callout--compact">
        <span className={`status-pulse${state.inventory.phase === 'error' ? ' status-pulse--amber' : ''}`} />
        {state.inventory.phase === 'ready'
          ? `V9 demo inventory · API · ${state.inventory.revision?.slice(0, 8)}`
          : state.inventory.message}
      </div>
      <label className="search-box">
        <Search size={14} aria-hidden="true" />
        <span className="sr-only">Filter V9 demo inventory devices</span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter devices" disabled={state.inventory.phase !== 'ready'} />
      </label>
      <div className="tree-heading"><ChevronDown size={14} aria-hidden="true" /> DEMO NETWORK</div>
      <div className="device-list" role="list" aria-label="V9 demo inventory devices">
        {state.inventory.phase === 'loading' && (
          <div className="empty-state" role="status"><LoaderCircle className="is-spinning" size={20} /><span>Loading V9 demo inventory…</span></div>
        )}
        {state.inventory.phase === 'error' && (
          <div className="empty-state" role="alert"><AlertTriangle size={20} /><span>{state.inventory.message}</span><button type="button" className="inventory-retry" onClick={retryInventory}><RefreshCw size={12} /> Retry inventory</button></div>
        )}
        {state.inventory.phase === 'empty' && <div className="empty-state"><Network size={20} /><span>The V9 demo inventory is empty.</span></div>}
        {state.inventory.phase === 'ready' && filtered.map((device) => {
          const selected = state.selectedDeviceId === device.id;
          return (
            <button
              type="button"
              role="listitem"
              key={device.id}
              className={`device-row${selected ? ' is-selected' : ''}`}
              aria-label={`${device.hostname} ${vendorLabel(device.vendor)} demo inventory device`}
              aria-current={selected ? 'true' : undefined}
              onClick={() => dispatch({ type: 'SELECT_DEVICE', deviceId: device.id })}
            >
              <span className={`device-icon vendor-${device.vendor}`}><RouterIcon /></span>
              <span className="device-copy">
                <span className="device-title"><strong>{device.hostname}</strong><span>{vendorLabel(device.vendor)}</span></span>
                <span className="device-meta">{titleCase(device.role)} · {device.site}</span>
              </span>
              <span className="demo-tag">DEMO</span>
            </button>
          );
        })}
        {state.inventory.phase === 'ready' && filtered.length === 0 && <div className="empty-state"><Network size={20} /><span>No inventory devices match.</span></div>}
      </div>
      <div className="explorer-detail">
        {(() => {
          const selected = state.devices.find((device) => device.id === state.selectedDeviceId);
          if (!selected) return null;
          return <>
            <span>Selected demo inventory</span>
            <strong>{selected.display_name}</strong>
            <small>{selected.platform} {selected.version} · {selected.location ?? selected.site}</small>
            <div className="device-facts"><span>{selected.interfaces.length} interfaces</span><span>{selected.capabilities.features.length} capabilities</span></div>
            {selected.tags.length > 0 && <div className="device-tags">{selected.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>}
          </>;
        })()}
      </div>
    </aside>
  );
}

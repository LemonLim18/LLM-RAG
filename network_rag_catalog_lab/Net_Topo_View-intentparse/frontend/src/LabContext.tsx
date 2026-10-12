import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { API_CONFIG } from './config';

import { LabContext, CapabilityContext, useLocalLab } from './localLab';
import type { PlatformCapabilities } from './localLab';

export function LabProvider({ children }: { children: ReactNode }) {
  const [local, setLocal] = useState<boolean | null>(null);
  const [error, setError] = useState('');
  const [capabilities, setCapabilities] = useState<PlatformCapabilities>({ mode: 'local_lab', features: {} });
  useEffect(() => {
    fetch(`${API_CONFIG.API_URL}/api/v1/lab/capabilities`)
      .then(async response => {
        if (response.status === 404) return { mode: 'normal' };
        if (!response.ok) throw new Error('Backend mode is unavailable');
        return response.json();
      })
      .then((data: PlatformCapabilities) => { setCapabilities(data); setLocal(data.mode === 'local_lab'); })
      .catch(() => setError('Cannot reach the CogniShield backend. Start backend/run_local.ps1, then reload.'));
  }, []);
  if (error) return <div className="p-8" role="alert">{error}</div>;
  if (local === null) return <div className="p-8">Connecting to CogniShield…</div>;
  return <CapabilityContext.Provider value={capabilities}><LabContext.Provider value={local}>{children}</LabContext.Provider></CapabilityContext.Provider>;
}

export function LocalLabBanner() {
  const local = useLocalLab();
  return local ? <div role="status" className="bg-warning/15 border-b border-warning/30 px-4 py-2 text-sm">
    <strong>Local lab</strong> · Inventory and authoring are stored in SQLite. Network observations are editable JSON simulations, not real measurements.
    Remote sync, SSH and physical deployment are unavailable. AI chat uses the configured local Ollama service.
  </div> : null;
}

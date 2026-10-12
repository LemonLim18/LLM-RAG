import { useState } from 'react';
import { useLocalLab } from '../src/localLab';
import { deployApi } from '../src/services/api';
import { Confirm, Toast } from '../src/utils/swal';

export function EnvironmentSelector() {
  const local = useLocalLab();
  const [switching, setSwitching] = useState(false);
  const change = async () => {
    const mode = local ? 'normal' : 'local_lab';
    const accepted = await Confirm.ask('Switch environment?', local
      ? 'Actual mode starts the original remote integrations using your .env settings. Remote services and normal-mode dependencies must be available. The backend will restart.'
      : 'Switch to SQLite and editable JSON providers. The backend will restart.');
    if (!accepted) return;
    setSwitching(true);
    try {
      const result = await deployApi.selectEnvironment(mode);
      if (!result.automatic_restart) {
        Toast.info('Environment saved', 'Restart using backend/run_local.ps1 to apply the .env selection, then reload.');
        return;
      }
      for (let attempt = 0; attempt < 30; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        try {
          if ((await deployApi.environment()).active_mode === mode) {
            window.location.reload();
            return;
          }
        } catch { /* Backend is restarting. */ }
      }
      Toast.error('Backend has not started', 'Check backend logs and normal-mode prerequisites. Set COGNISHIELD_MODE=local_lab in .env to return to local mode.');
    } catch (error: any) {
      Toast.error('Environment switch failed', error.message);
    } finally { setSwitching(false); }
  };
  return <label className="flex items-center gap-2 text-xs" title="Environment selected by COGNISHIELD_MODE in .env">
    <span>{switching ? 'Switching…' : local ? 'Local simulation' : 'Actual environment'}</span>
    <input aria-label="Use actual environment" type="checkbox" className="toggle toggle-sm toggle-primary" checked={!local} disabled={switching} onChange={change} />
  </label>;
}

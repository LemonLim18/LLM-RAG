import { Braces, Cloud, CloudOff, Github, LoaderCircle, Radio, RefreshCw, TriangleAlert } from 'lucide-react';
import { useWorkbench } from '../../app/workbenchContext';
import { useBackendStatus } from '../../features/connectivity/useBackendStatus';

const authorityLabel = {
  direct_files: 'Direct files',
  published_release: 'Published release',
} as const;

export function StatusBar() {
  const { state } = useWorkbench();
  const { connection, retry } = useBackendStatus();
  const device = state.devices.find((item) => item.id === state.selectedDeviceId);
  const authority = connection.phase === 'connected'
    ? connection.snapshot.runtime.knowledge.effective_runtime_authority
    : null;
  const ConnectionIcon = connection.phase === 'connected'
    ? Cloud
    : connection.phase === 'loading'
      ? LoaderCircle
      : connection.phase === 'error'
        ? TriangleAlert
        : CloudOff;
  return (
    <footer className="status-bar" aria-label="Workbench status">
      <span className="status-bar-brand"><Braces size={13} /> Network Workbench</span>
      <span><Radio size={12} /> {device?.hostname ?? 'No device'} selected</span>
      <span className={`connection-state connection-state--${connection.phase}`} role="status">
        <ConnectionIcon size={12} className={connection.phase === 'loading' ? 'is-spinning' : undefined} />
        {connection.message}{authority ? ` · ${authorityLabel[authority]}` : ''}
      </span>
      {connection.phase === 'connected' && (
        <span title="Health requests do not probe Ollama, embeddings, or Chroma">AI {connection.snapshot.runtime.llm.status.replace('_', ' ')}</span>
      )}
      {(connection.phase === 'disconnected' || connection.phase === 'error') && (
        <button type="button" className="status-retry" onClick={retry} aria-label="Retry backend connection"><RefreshCw size={11} /> Retry</button>
      )}
      <span className="status-bar-spacer" />
      <span><Github size={12} /> Iteration 9</span>
      <span>Local preview only</span>
    </footer>
  );
}

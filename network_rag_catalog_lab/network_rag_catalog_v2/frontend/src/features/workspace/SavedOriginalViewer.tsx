import Editor from '@monaco-editor/react';
import { useWorkbench } from '../../app/workbenchContext';
import { configureNetworkLanguage } from './monacoSetup';

export function SavedOriginalViewer() {
  const { originals, dispatch, working } = useWorkbench();
  const { opened } = originals;
  if (opened.phase === 'loading') return <p className="empty-state" role="status">Opening saved original…</p>;
  if (opened.phase === 'error') return <div className="empty-state" role="alert">{opened.error}
    <button type="button" onClick={() => void originals.open(opened.id)}>Retry reading original</button></div>;
  const record = opened.artifact;
  if (!record) return <p className="empty-state">Select a saved original from Explorer.</p>;
  const path = `inmemory://v9-original/${record.artifact_id}/configuration`;
  return <section className="generated-editor" aria-label="Saved original document">
    <header className="generated-editor__provenance">
      <div><strong>Saved V9 original · READ-ONLY</strong>
        <button type="button" disabled={working.opening.pending} onClick={() => void working.prepare(record.artifact_id)}>Open for Editing</button>
        <button type="button" onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'samples' })}>Back to samples</button></div>
      <p>{record.hostname ?? record.source.device_id} · {record.vendor ?? 'Vendor not reported'} · {record.platform ?? 'Platform not reported'} · {record.operation_id ?? 'Operation not reported'}</p>
      <details><summary>Original identity and captured provenance</summary><dl>
        <dt>Original</dt><dd>{record.artifact_id}</dd><dt>Captured</dt><dd>{record.captured_at}</dd>
        <dt>Source session</dt><dd>{record.source.session_id}</dd><dt>Saved source revision</dt><dd>{record.source.session_revision}</dd>
        <dt>Task</dt><dd>{record.source.task_id}</dd><dt>Logical intent</dt><dd>{record.logical_intent_id ?? 'Not reported'}</dd>
        <dt>Device</dt><dd>{record.source.device_id}</dd><dt>Configuration entry</dt><dd>{record.source.config_index}</dd>
        <dt>Content SHA-256 (UTF-8)</dt><dd>{record.content_sha256}</dd>
        {Object.entries(record.authority).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value || 'Not reported'}</dd></div>)}
      </dl></details>
      <p className="saved-state-notice">Historical captured output · current validity not checked · not deployed</p>
      <small>Immutable workspace original, not a draft, sample or published template. No save-back or execution.</small>
    </header>
    <div className="monaco-host"><Editor key={path} path={path} value={record.configuration} language="network-cli" theme="network-workbench"
      beforeMount={configureNetworkLanguage} keepCurrentModel={false} saveViewState={false}
      loading={<div className="editor-loading">Loading read-only saved original…</div>}
      options={{ readOnly: true, domReadOnly: true, ariaLabel: 'Read-only saved original editor', automaticLayout: true,
        minimap: { enabled: false }, fontSize: 13, lineHeight: 21, fontFamily: "'Cascadia Code', Consolas, monospace",
        scrollBeyondLastLine: false, padding: { top: 14, bottom: 14 }, wordWrap: 'off', renderWhitespace: 'selection' }} /></div>
  </section>;
}

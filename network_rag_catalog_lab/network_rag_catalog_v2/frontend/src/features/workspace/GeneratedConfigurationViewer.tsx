import Editor from '@monaco-editor/react';
import { useWorkbench } from '../../app/workbenchContext';
import { configureNetworkLanguage } from './monacoSetup';
import { previewModelPath, resolveGeneratedPreview } from './generatedPreview';
import { GeneratedWorkingAction } from './GeneratedWorkingAction';

export function GeneratedConfigurationViewer() {
  const { state, dispatch, localPlanning, originals } = useWorkbench();
  const result = localPlanning.state.result;
  const selection = state.generatedPreview;
  const output = resolveGeneratedPreview(result, selection);
  if (!output || !selection || !result) return <div className="empty-state" role="status">
    This output is no longer available in the confirmed session. Open a current configuration from V9 Plan Review.
  </div>;
  const { task, config } = output;
  const reported = (field: string) => typeof config[field] === 'string' ? config[field] as string : 'Not reported';
  const path = previewModelPath(selection);
  return <section className="generated-editor" aria-label="Read-only V9 configuration">
    <header className="generated-editor__provenance">
      <div><strong>V9-generated preview · READ-ONLY</strong>
        <GeneratedWorkingAction result={result} task={task} index={selection.configIndex} label="Open for Editing" />
        <button type="button" disabled={originals.capture.phase === 'loading'} onClick={() => void originals.save(selection)}>Save to Workspace</button>
        <button type="button" onClick={() => dispatch({ type: 'CLOSE_GENERATED_PREVIEW' })}>Close preview</button></div>
      <p>{reported('hostname')} · {reported('vendor')} · {reported('platform')} · Output {selection.configIndex + 1}</p>
      <details><summary>Session, task and device provenance</summary>
        <dl><dt>Session</dt><dd>{selection.sessionId}</dd><dt>Saved revision</dt><dd>{selection.sessionRevision}</dd>
          <dt>Task</dt><dd>{task.intent_id}</dd><dt>Logical intent</dt><dd>{task.logical_intent_id || 'Not reported'}</dd>
          <dt>Device</dt><dd>{config.device_id}</dd><dt>Operation</dt><dd>{task.operation_id || 'Not reported'}</dd>
          <dt>Task status</dt><dd>{task.status}</dd><dt>Runtime authority</dt><dd>{result.session.plan.runtime_authority || 'Not reported'}</dd>
          <dt>Knowledge snapshot</dt><dd>{result.session.plan.knowledge_snapshot_id || 'Not reported'}</dd></dl>
      </details>
      {localPlanning.state.historical && <p className="saved-state-notice">Saved historical state · current validity not checked</p>}
      <small>Confirmed session output · preview only, not deployed · not an editable sample or separately persisted artifact</small>
      {originals.capture.key === JSON.stringify(selection) && originals.capture.message &&
        <p role={originals.capture.phase === 'error' ? 'alert' : 'status'}>{originals.capture.message}</p>}
    </header>
    <div className="monaco-host">
      <Editor key={path} path={path} value={config.configuration} language="network-cli" theme="network-workbench"
        beforeMount={configureNetworkLanguage} keepCurrentModel={false} saveViewState={false}
        loading={<div className="editor-loading">Loading read-only local Monaco preview…</div>}
        options={{ readOnly: true, domReadOnly: true, ariaLabel: 'Read-only V9 configuration editor',
          automaticLayout: true, minimap: { enabled: false }, fontSize: 13, lineHeight: 21,
          fontFamily: "'Cascadia Code', Consolas, monospace", scrollBeyondLastLine: false,
          padding: { top: 14, bottom: 14 }, wordWrap: 'off', renderWhitespace: 'selection' }} />
    </div>
  </section>;
}

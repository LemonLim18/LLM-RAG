import { Braces, ListTree, RotateCcw } from 'lucide-react';
import { useWorkbench } from '../../app/workbenchContext';
import { ConfigurationEditor } from './ConfigurationEditor';
import { EditorTabs } from './EditorTabs';
import { TaskReviewPanel } from './TaskReviewPanel';
import { GeneratedConfigurationViewer } from './GeneratedConfigurationViewer';
import { resolveGeneratedPreview } from './generatedPreview';
import { SavedOriginalViewer } from './SavedOriginalViewer';
import { WorkingEditor } from './WorkingEditor';

export function WorkspacePanel() {
  const { state, dispatch, localPlanning, originals, working } = useWorkbench();
  const document = state.documents[state.activeTabId];
  const reviewing = state.workspaceView === 'plan' && Boolean(localPlanning.state.result);
  const previewing = state.workspaceView === 'preview';
  const original = state.workspaceView === 'original';
  const editing = state.workspaceView === 'working';
  const previewAvailable = Boolean(resolveGeneratedPreview(localPlanning.state.result, state.generatedPreview));
  return (
    <main className={`workspace-panel${reviewing || previewing || original || editing ? ' workspace-panel--review' : ''}`} aria-label="Configuration workspace">
      <div className="workspace-titlebar">
        <div><Braces size={15} /><span>CONFIGURATION WORKSPACE</span>
          <div className="workspace-view-switch" role="tablist" aria-label="Workspace view">
            <button type="button" role="tab" aria-selected={!reviewing && !previewing && !original && !editing} onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'samples' })}><Braces size={12} />Samples</button>
            <button type="button" role="tab" aria-selected={editing} disabled={!working.activeId} onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'working' })}>Working files</button>
            <button type="button" role="tab" aria-selected={reviewing} disabled={!localPlanning.state.result} onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'plan' })}><ListTree size={12} />V9 plan review</button>
            <button type="button" role="tab" aria-selected={previewing} disabled={!previewAvailable} onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'preview' })}>V9 preview</button>
            <button type="button" role="tab" aria-selected={original} disabled={!originals.opened.id} onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'original' })}>Saved original</button>
          </div>
        </div>
        <div className="workspace-actions">
          {editing ? <span className="workspace-state">UNVALIDATED</span> : reviewing || previewing || original ? <span className="workspace-state workspace-state--v9">READ-ONLY</span> : <>
            <span className="workspace-state"><span className="status-pulse status-pulse--amber" />In-memory demo</span>
            <span title="Reload the page to reset all demo edits"><RotateCcw size={13} /> resets on reload</span>
          </>}
        </div>
      </div>
      {editing ? <><WorkingEditor /><div className="workspace-statusline"><span>Working document · local save only · no execution</span></div></> : original ? <>
        <SavedOriginalViewer />
        <div className="workspace-statusline"><span>Persisted immutable snapshot · read-only · no execution</span></div>
      </> : previewing ? <>
        <GeneratedConfigurationViewer />
        <div className="workspace-statusline"><span>Transient V9 output · explicit capture only · no execution</span></div>
      </> : reviewing ? <>
        <div className="plan-review-container">
          {state.previewNotice && <p className="preview-notice" role="status">{state.previewNotice}</p>}
          <TaskReviewPanel />
        </div>
        <div className="workspace-statusline"><span>V9 session {localPlanning.state.result?.session.session_id}</span><span>Preview only · no execution</span></div>
      </> : <>
        <EditorTabs />
        <ConfigurationEditor />
        <div className="workspace-statusline">
          <span>{document?.dirty ? 'Modified locally' : 'Sample original loaded'}</span>
          <span>{document?.vendor.toUpperCase()} · Network CLI · UTF-8 · LF</span>
        </div>
      </>}
    </main>
  );
}

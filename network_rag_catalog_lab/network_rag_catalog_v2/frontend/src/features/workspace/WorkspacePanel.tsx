import { Braces, ListTree, RotateCcw } from 'lucide-react';
import { useWorkbench } from '../../app/workbenchContext';
import { ConfigurationEditor } from './ConfigurationEditor';
import { EditorTabs } from './EditorTabs';
import { TaskReviewPanel } from './TaskReviewPanel';

export function WorkspacePanel() {
  const { state, dispatch, localPlanning } = useWorkbench();
  const document = state.documents[state.activeTabId];
  const reviewing = state.workspaceView === 'plan' && Boolean(localPlanning.state.result);
  return (
    <main className={`workspace-panel${reviewing ? ' workspace-panel--review' : ''}`} aria-label="Configuration workspace">
      <div className="workspace-titlebar">
        <div><Braces size={15} /><span>CONFIGURATION WORKSPACE</span>
          <div className="workspace-view-switch" role="tablist" aria-label="Workspace view">
            <button type="button" role="tab" aria-selected={!reviewing} onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'samples' })}><Braces size={12} />Samples</button>
            <button type="button" role="tab" aria-selected={reviewing} disabled={!localPlanning.state.result} onClick={() => dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'plan' })}><ListTree size={12} />V9 plan review</button>
          </div>
        </div>
        <div className="workspace-actions">
          {reviewing ? <span className="workspace-state workspace-state--v9">READ-ONLY SESSION REVIEW</span> : <>
            <span className="workspace-state"><span className="status-pulse status-pulse--amber" />In-memory demo</span>
            <span title="Reload the page to reset all demo edits"><RotateCcw size={13} /> resets on reload</span>
          </>}
        </div>
      </div>
      {reviewing ? <>
        <TaskReviewPanel />
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

import { Bot, PanelBottom, PanelLeft, PanelRight } from 'lucide-react';
import { useCallback } from 'react';
import { useWorkbench } from '../../app/workbenchContext';
import { ActivityPanel } from '../../features/activity/ActivityPanel';
import { ChatPanel } from '../../features/chat/ChatPanel';
import { ExplorerPanel } from '../../features/explorer/ExplorerPanel';
import { WorkspacePanel } from '../../features/workspace/WorkspacePanel';
import { ResizeHandle } from './ResizeHandle';
import { StatusBar } from './StatusBar';

export function WorkbenchLayout() {
  const { state, dispatch } = useWorkbench();
  const { layout } = state;
  const resize = useCallback((panel: 'explorer' | 'copilot' | 'activity', value: number) => dispatch({ type: 'RESIZE_PANEL', panel, value }), [dispatch]);

  return (
    <div className="workbench-shell">
      <header className="app-header">
        <div className="brand-mark"><Bot size={17} /></div>
        <div className="brand-copy"><strong>Network Orchestration Workbench</strong><span>AI-assisted configuration studio</span></div>
        <div className="global-demo-banner"><span className="status-pulse status-pulse--amber" /> LOCAL PREVIEW · SYNTHETIC INVENTORY · SAMPLE EDITS RESET ON RELOAD</div>
        <nav className="panel-controls" aria-label="Toggle workbench panels">
          <button type="button" className={layout.explorerVisible ? 'is-active' : ''} aria-label="Toggle infrastructure explorer" aria-pressed={layout.explorerVisible} onClick={() => dispatch({ type: 'TOGGLE_PANEL', panel: 'explorer' })}><PanelLeft size={15} /></button>
          <button type="button" className={layout.activityVisible ? 'is-active' : ''} aria-label="Toggle activity panel" aria-pressed={layout.activityVisible} onClick={() => dispatch({ type: 'TOGGLE_PANEL', panel: 'activity' })}><PanelBottom size={15} /></button>
          <button type="button" className={layout.copilotVisible ? 'is-active' : ''} aria-label="Toggle AI Copilot" aria-pressed={layout.copilotVisible} onClick={() => dispatch({ type: 'TOGGLE_PANEL', panel: 'copilot' })}><PanelRight size={15} /></button>
        </nav>
      </header>

      <div className="workbench-body">
        <div className="workbench-columns">
          {layout.explorerVisible && <><div style={{ width: layout.explorerWidth }} className="explorer-slot"><ExplorerPanel /></div><ResizeHandle orientation="vertical" label="Resize infrastructure explorer" value={layout.explorerWidth} min={190} max={380} onChange={(value) => resize('explorer', value)} /></>}
          <div className="center-column">
            <WorkspacePanel />
            {layout.activityVisible && <><ResizeHandle orientation="horizontal" label="Resize activity panel" value={layout.activityHeight} min={120} max={360} direction={-1} onChange={(value) => resize('activity', value)} /><div style={{ height: layout.activityHeight }} className="activity-slot"><ActivityPanel /></div></>}
          </div>
          {layout.copilotVisible && <><ResizeHandle orientation="vertical" label="Resize AI Copilot" value={layout.copilotWidth} min={280} max={480} direction={-1} onChange={(value) => resize('copilot', value)} /><div style={{ width: layout.copilotWidth }} className="copilot-slot"><ChatPanel /></div></>}
        </div>
      </div>
      <StatusBar />
    </div>
  );
}

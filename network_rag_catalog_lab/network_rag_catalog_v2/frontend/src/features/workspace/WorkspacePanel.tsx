import { Braces, RotateCcw } from 'lucide-react';
import { useWorkbench } from '../../app/workbenchContext';
import { ConfigurationEditor } from './ConfigurationEditor';
import { EditorTabs } from './EditorTabs';

export function WorkspacePanel() {
  const { state } = useWorkbench();
  const document = state.documents[state.activeTabId];
  return (
    <main className="workspace-panel" aria-label="Configuration workspace">
      <div className="workspace-titlebar">
        <div><Braces size={15} /><span>CONFIGURATION WORKSPACE</span></div>
        <div className="workspace-actions">
          <span className="workspace-state"><span className="status-pulse status-pulse--amber" />In-memory demo</span>
          <span title="Reload the page to reset all demo edits"><RotateCcw size={13} /> resets on reload</span>
        </div>
      </div>
      <EditorTabs />
      <ConfigurationEditor />
      <div className="workspace-statusline">
        <span>{document?.dirty ? 'Modified locally' : 'Sample original loaded'}</span>
        <span>{document?.vendor.toUpperCase()} · Network CLI · UTF-8 · LF</span>
      </div>
    </main>
  );
}

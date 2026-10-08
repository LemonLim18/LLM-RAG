import { Circle } from 'lucide-react';
import { useWorkbench } from '../../app/workbenchContext';

export function EditorTabs() {
  const { state, dispatch } = useWorkbench();
  return (
    <div className="editor-tabs" role="tablist" aria-label="Open sample configurations">
      {state.openTabIds.map((tabId) => {
        const document = state.documents[tabId];
        const active = tabId === state.activeTabId;
        return (
          <button
            type="button"
            key={tabId}
            id={`tab-${tabId}`}
            role="tab"
            aria-selected={active}
            aria-controls="configuration-editor"
            className={`editor-tab${active ? ' is-active' : ''}`}
            onClick={() => dispatch({ type: 'ACTIVATE_TAB', tabId })}
          >
            <span className={`vendor-mark vendor-${document.vendor}`} />
            <span>{document.name}</span>
            {document.dirty && <Circle size={8} fill="currentColor" aria-label="Unsaved in-memory edits" />}
          </button>
        );
      })}
    </div>
  );
}

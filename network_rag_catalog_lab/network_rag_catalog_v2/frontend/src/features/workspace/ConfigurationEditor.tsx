import Editor from '@monaco-editor/react';
import { AlertTriangle, FileCode2 } from 'lucide-react';
import { useState } from 'react';
import { useWorkbench } from '../../app/workbenchContext';
import { configureNetworkLanguage } from './monacoSetup';

export function ConfigurationEditor() {
  const { state, dispatch } = useWorkbench();
  const [loadError, setLoadError] = useState(false);
  const document = state.documents[state.activeTabId];

  if (!document) {
    return <div className="empty-state empty-state--editor"><FileCode2 /><span>Select a sample device to open a configuration.</span></div>;
  }

  if (loadError) {
    return (
      <div className="empty-state empty-state--editor" role="alert">
        <AlertTriangle />
        <span>Monaco could not load. Check the local development console and reload.</span>
      </div>
    );
  }

  return (
    <div className="editor-stage" id="configuration-editor" role="tabpanel" aria-labelledby={`tab-${document.id}`}>
      <div className="editor-context-bar">
        <span><strong>{document.hostname}</strong> · {document.vendor} · {document.platform} {document.version}</span>
        <span className="validation-badge">UNVALIDATED WORKING COPY</span>
      </div>
      <div className="monaco-host">
        <Editor
          path={`inmemory://demo/${document.id}/${document.name}`}
          language={document.language}
          theme="network-workbench"
          value={document.content}
          beforeMount={configureNetworkLanguage}
          onChange={(value) => dispatch({ type: 'UPDATE_DOCUMENT', tabId: document.id, content: value ?? '' })}
          onValidate={() => setLoadError(false)}
          loading={<div className="editor-loading">Loading local Monaco editor…</div>}
          options={{
            ariaLabel: 'Configuration editor',
            automaticLayout: true,
            minimap: { enabled: false },
            fontFamily: "'Cascadia Code', 'SFMono-Regular', Consolas, monospace",
            fontSize: 13,
            lineHeight: 21,
            lineNumbersMinChars: 3,
            padding: { top: 14, bottom: 14 },
            scrollBeyondLastLine: false,
            smoothScrolling: true,
            wordWrap: 'off',
            tabSize: 2,
            renderWhitespace: 'selection',
            bracketPairColorization: { enabled: true },
          }}
          onMount={(editor) => {
            setLoadError(false);
            editor.focus();
          }}
        />
      </div>
    </div>
  );
}

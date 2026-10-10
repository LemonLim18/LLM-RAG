import { useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { editor } from 'monaco-editor/editor/editor.api';
import { useWorkbench } from '../../app/workbenchContext';
import { configureNetworkLanguage } from './monacoSetup';

// Retained during inline review: the diff owns separate models, never this buffer.
export function WorkingTextEditor({ id, content, reviewing }: { id: string; content: string; reviewing: boolean }) {
  const { working } = useWorkbench();
  const instance = useRef<editor.IStandaloneCodeEditor | null>(null);
  const changing = useRef(false);
  useEffect(() => {
    const current = instance.current;
    const model = current?.getModel();
    // Explicit saved-state reconciliation, not proposal preview. No setValue/undo reset.
    if (current && model && model.getValue(undefined, true) !== content) {
      changing.current = true;
      current.pushUndoStop();
      current.executeEdits('saved-state-reconciliation', [{ range: model.getFullModelRange(), text: content }]);
      current.pushUndoStop();
      changing.current = false;
    }
  }, [content]);
  useEffect(() => {
    if (!reviewing) { instance.current?.layout(); instance.current?.focus(); }
  }, [reviewing]);
  return <div className="working-buffer-host" hidden={reviewing} aria-hidden={reviewing}>
    <Editor path={`inmemory://v9-working/${id}/configuration`} defaultValue={content} language="network-cli" theme="network-workbench"
      beforeMount={configureNetworkLanguage} keepCurrentModel={false} saveViewState={false}
      onMount={(current) => {
        instance.current = current;
        const model = current.getModel()!;
        const change = model.onDidChangeContent(() => {
          if (!changing.current) working.edit(id, model.getValue(undefined, true));
        });
        const disconnect = working.connectEditor(id, {
          read: () => model.getValue(undefined, true),
          focus: () => current.focus(),
          replace: (text) => {
            // Monaco normalizes EOLs and treats the initial BOM as model metadata.
            // Never silently normalize an exact proposed string during acceptance.
            const before = model.getValue(undefined, true);
            const endings = [...new Set([...text.matchAll(/\r\n|\r|\n/g)].map((match) => match[0]))];
            if (before.startsWith('\uFEFF') !== text.startsWith('\uFEFF') || endings.length > 1 || endings[0] === '\r') return false;
            const view = current.saveViewState();
            changing.current = true;
            // executeEdits refuses a readOnly editor, including programmatic edits.
            // Unlock only this hidden buffer for the synchronous, guarded operation.
            current.updateOptions({ readOnly: false });
            let applied: boolean;
            try {
              current.pushUndoStop();
              if (endings[0] && endings[0] !== model.getEOL()) model.pushEOL(endings[0] === '\n' ? editor.EndOfLineSequence.LF : editor.EndOfLineSequence.CRLF);
              applied = current.executeEdits('accept-working-proposal', [{ range: model.getFullModelRange(), text: text.replace(/^\uFEFF/, '') }]);
              current.pushUndoStop();
            } finally { changing.current = false; current.updateOptions({ readOnly: true }); }
            if (view) current.restoreViewState(view);
            return applied && model.getValue(undefined, true) === text;
          },
        });
        current.onDidDispose(() => { change.dispose(); disconnect(); if (instance.current === current) instance.current = null; });
        current.focus();
      }}
      options={{ readOnly: reviewing, domReadOnly: reviewing, ariaLabel: 'Working configuration editor', automaticLayout: true,
        minimap: { enabled: false }, autoIndent: 'none', fontSize: 13, lineHeight: 21,
        fontFamily: "'Cascadia Code', Consolas, monospace", scrollBeyondLastLine: false }} />
  </div>;
}

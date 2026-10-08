import { loader } from '@monaco-editor/react';
import * as monaco from 'monaco-editor/editor/editor.api';
import EditorWorker from 'monaco-editor/editor/editor.worker?worker';

self.MonacoEnvironment = {
  getWorker() {
    return new EditorWorker();
  },
};

loader.config({ monaco });

export function configureNetworkLanguage(monacoApi: typeof monaco) {
  if (!monacoApi.languages.getLanguages().some((language) => language.id === 'network-cli')) {
    monacoApi.languages.register({ id: 'network-cli', aliases: ['Network CLI'] });
    monacoApi.languages.setMonarchTokensProvider('network-cli', {
      ignoreCase: true,
      tokenizer: {
        root: [
          [/^\s*[!#].*$/, 'comment'],
          [/\b(interface|router|ospf|network|hostname|sysname|system|interfaces|routing-options|area|vlan|name|description|address|return|end)\b/, 'keyword'],
          [/\b(ip|ipv4|inet|switchport|unit|family|mode|access|router-id)\b/, 'type'],
          [/\b\d{1,3}(?:\.\d{1,3}){3}(?:\/\d{1,2})?\b/, 'number'],
          [/\b\d+\b/, 'number'],
          [/[{};]/, 'delimiter'],
          [/"[^"\\]*(?:\\.[^"\\]*)*"/, 'string'],
        ],
      },
    });
  }

  monacoApi.editor.defineTheme('network-workbench', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '64748B', fontStyle: 'italic' },
      { token: 'keyword', foreground: '60A5FA' },
      { token: 'type', foreground: 'A78BFA' },
      { token: 'number', foreground: 'FBBF24' },
      { token: 'string', foreground: '86EFAC' },
    ],
    colors: {
      'editor.background': '#0b1120',
      'editor.foreground': '#d6deeb',
      'editorLineNumber.foreground': '#334155',
      'editorLineNumber.activeForeground': '#94a3b8',
      'editor.selectionBackground': '#1d4ed866',
      'editorCursor.foreground': '#38bdf8',
      'editorIndentGuide.background1': '#1e293b',
    },
  });
}

import type { Monaco } from '@monaco-editor/react';

/** One language decision for buffers, previews and diffs, including renamed files. */
export function languageForDocument(path: string, content = ''): string {
  const extension = path.toLowerCase().split('.').pop() || '';
  if (['j2', 'jinja', 'jinja2'].includes(extension) ||
      (['yaml', 'yml', 'cfg', 'conf', 'txt'].includes(extension) && /\{[{%#]/.test(content))) return 'jinja2';
  return ({ yml: 'yaml', yaml: 'yaml', json: 'json', py: 'python', md: 'markdown',
    sh: 'shell', bash: 'shell', ini: 'ini', xml: 'xml', html: 'html', js: 'javascript',
    ts: 'typescript', css: 'css', sql: 'sql', cfg: 'network-config', conf: 'network-config' } as Record<string, string>)[extension] || 'plaintext';
}

export function registerEditorLanguages(monaco: Monaco) {
  for (const id of ['jinja2', 'network-config', 'ke-jinja', 'nettopo-jinja']) {
    if (monaco.languages.getLanguages().some((language: {id: string}) => language.id === id)) continue;
    monaco.languages.register({ id, ...(id === 'jinja2' ? { extensions: ['.j2', '.jinja', '.jinja2'], aliases: ['Jinja2'] } : {}) });
    monaco.languages.setLanguageConfiguration(id, {
      comments: { blockComment: ['{#', '#}'] },
      brackets: [['{', '}'], ['[', ']'], ['(', ')']],
      autoClosingPairs: [{ open: '"', close: '"' }, { open: "'", close: "'" }, { open: '(', close: ')' }, { open: '[', close: ']' }],
    });
    monaco.languages.setMonarchTokensProvider(id, {
      tokenizer: {
        root: [
          [/\{%-?\s*raw\s*-?%\}/, 'keyword', '@raw'],
          [/\{#/, 'comment', '@comment'], [/\{\{-?/, 'delimiter', '@expression'], [/\{%-?/, 'delimiter', '@statement'],
          [/#.*$/, 'comment'], [/^\s*[\w.-]+(?=\s*:)/, 'variable'],
          [/\b(?:interface|router|neighbor|set|delete|ip|ipv6|ospf|bgp|undo|route-policy|policy-options|protocols)\b/, 'keyword'],
          [/"/, 'string', '@outerDouble'], [/'/, 'string', '@outerSingle'],
          [/\b(?:true|false|null|yes|no)\b/, 'keyword'], [/\b\d+(?:\.\d+)*\b/, 'number'],
          [/[\[\]:,>-]/, 'delimiter'], [/[^\s{#"'\w\[\]:,>-]+/, ''], [/\w+|\s+|./, ''],
        ],
        raw: [[/\{%-?\s*endraw\s*-?%\}/, 'keyword', '@pop'], [/./, '']],
        comment: [[/#\}/, 'comment', '@pop'], [/[^#]+|#/, 'comment']],
        expression: [[/-?\}\}/, 'delimiter', '@pop'], { include: '@body' }],
        statement: [[/-?%\}/, 'delimiter', '@pop'], { include: '@body' }],
        nested: [[/\}/, 'delimiter', '@pop'], { include: '@body' }],
        body: [
          [/\{/, 'delimiter', '@nested'], [/"/, 'string', '@double'], [/'/, 'string', '@single'],
          [/\b(?:if|else|elif|endif|for|endfor|in|is|defined|and|or|not|set|true|false|none|True|False|None|with|endwith|block|endblock|macro|endmacro|filter|endfilter|include|extends|import|from|as|recursive|call|endcall|do)\b/, 'keyword'],
          [/(\|\s*)([\w]+)/, ['operator', 'predefined']], [/\.[a-zA-Z_]\w*/, 'variable.member'],
          [/\d+(?:\.\d+)?/, 'number'], [/[a-zA-Z_]\w*/, 'variable.name'],
          [/[-+*=<>!/~%]+/, 'operator'], [/[()[\],:]/, 'delimiter'], [/\s+|./, ''],
        ],
        double: [[/\\./, 'string.escape'], [/"/, 'string', '@pop'], [/[^"\\]+/, 'string']],
        single: [[/\\./, 'string.escape'], [/'/, 'string', '@pop'], [/[^'\\]+/, 'string']],
        outerDouble: [[/\{\{-?/, 'delimiter', '@expression'], [/\{%-?/, 'delimiter', '@statement'], [/\\./, 'string.escape'], [/"/, 'string', '@pop'], [/[^"\\{]+|\{/, 'string']],
        outerSingle: [[/\{\{-?/, 'delimiter', '@expression'], [/\{%-?/, 'delimiter', '@statement'], [/'/, 'string', '@pop'], [/[^'{]+|\{/, 'string']],
      },
    });
  }
}

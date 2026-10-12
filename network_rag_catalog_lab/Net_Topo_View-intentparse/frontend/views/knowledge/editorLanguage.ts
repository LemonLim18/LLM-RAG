import type { BeforeMount } from '@monaco-editor/react';

// Scoped editor languages/themes for the Knowledge Engineering reference design.
export const configureKnowledgeEditor: BeforeMount = monaco => {
  if (!monaco.languages.getLanguages().some((language: {id: string}) => language.id === 'ke-jinja')) {
    monaco.languages.register({id:'ke-jinja'});
    monaco.languages.setMonarchTokensProvider('ke-jinja', {
      tokenizer: {
        root: [
          [/\{#/, 'comment', '@comment'],
          [/\{[%{]-?/, 'delimiter', '@expression'],
          [/^\s*(?:no\s+)?(?:vlan|name|description|shutdown|interface|switchport)\b/, 'command'],
          [/[^\{]+/, 'text'],
        ],
        comment: [[/[^#]+/, 'comment'], [/#\}/, 'comment', '@pop'], [/#/, 'comment']],
        expression: [
          [/-?[%}]\}/, 'delimiter', '@pop'],
          [/\b(?:if|else|elif|endif|for|endfor|in|is|defined|and|or|not|set|true|false|none)\b/, 'keyword'],
          [/'[^']*'|"[^"]*"/, 'string'],
          [/\d+/, 'number'],
          [/[a-zA-Z_][\w.]*/, 'variable'],
          [/[=<>!|]+/, 'operator'],
          [/\s+/, 'white'],
        ],
      },
    });
    monaco.languages.register({id:'ke-json'});
    monaco.languages.setMonarchTokensProvider('ke-json', {tokenizer:{root:[
      [/"[^"]*"(?=\s*:)/,'variable'],[/"[^"]*"/,'jsonstring'],[/\b(?:true|false|null)\b/,'keyword'],
      [/-?\d+(?:\.\d+)?/,'number'],[/[{}\[\],:]/,'delimiter'],
    ]}});
  }
  monaco.editor.defineTheme('ke-reference', {
    base:'vs-dark', inherit:true,
    rules:[
      {token:'comment',foreground:'718B9F'}, {token:'command',foreground:'FFBA32'},
      {token:'keyword',foreground:'55D3FF'}, {token:'variable',foreground:'63D2FF'},
      {token:'string',foreground:'FF7352'}, {token:'jsonstring',foreground:'A8E45C'},
      {token:'number',foreground:'65DEDF'}, {token:'delimiter',foreground:'DDDFF3'},
      {token:'operator',foreground:'B795FF'}, {token:'text',foreground:'BED4E5'},
    ],
    colors:{'editor.background':'#09151F','editor.foreground':'#BED4E5',
      'editorLineNumber.foreground':'#62839F','editorLineNumber.activeForeground':'#BFD5E8',
      'editor.selectionBackground':'#153D66','editor.lineHighlightBorder':'#142532',
      'editorGutter.background':'#09151F'},
  });
};


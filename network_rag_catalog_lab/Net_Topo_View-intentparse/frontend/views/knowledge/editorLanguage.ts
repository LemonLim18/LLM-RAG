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
};

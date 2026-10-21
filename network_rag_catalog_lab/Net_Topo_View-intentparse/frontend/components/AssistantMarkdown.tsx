import { isValidElement, useEffect, useState, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy } from 'lucide-react';
import { loader } from '@monaco-editor/react';
import { chatLanguage, copyMarkdown, tokenSegments } from '../src/utils/assistantCode';

function CopyAction({ content, response = false }: { content: string; response?: boolean }) {
  const [state, setState] = useState<'idle' | 'copying' | 'copied' | 'failed'>('idle');
  useEffect(() => {
    if (state !== 'copied' && state !== 'failed') return;
    const timer = setTimeout(() => setState('idle'), 2400);
    return () => clearTimeout(timer);
  }, [state]);
  async function copy() {
    setState('copying');
    setState(await copyMarkdown(content, value => navigator.clipboard.writeText(value)));
  }
  return <span className="assistant-copy-action"><button type="button" disabled={state === 'copying'} aria-label={response ? 'Copy response' : 'Copy code'} onClick={() => void copy()}>
    {state === 'copied' ? <Check size={14} /> : <Copy size={14} />}
    {state === 'copied' ? 'Copied' : state === 'failed' ? 'Try copying again' : response ? 'Copy response' : 'Copy'}
  </button><span role="status" aria-live="polite" className={state === 'failed' ? 'assistant-copy-error' : 'sr-only'}>{state === 'failed' ? 'Copy failed. Select the text and copy it manually, or try again.' : state === 'copied' ? 'Copied to clipboard.' : ''}</span></span>;
}

export function CopyResponse({ content }: { content: string }) {
  return <div className="assistant-response-actions"><CopyAction content={content} response /></div>;
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const code = isValidElement<{children?: ReactNode; className?: string}>(children) ? children.props : {};
  const text = String(code.children ?? '').replace(/\n$/, '');
  const fence = String(code.className || '').replace('language-', '');
  const language = chatLanguage(fence, text);
  const [lines, setLines] = useState<ReturnType<typeof tokenSegments>[]>([]);
  useEffect(() => {
    let current = true;
    setLines([]);
    // Large blocks stay complete/copyable; only syntax work is bounded.
    if (language === 'plaintext' || text.length > 50000 || text.split('\n').length > 2000) return;
    void loader.init().then(async monaco => {
      await monaco.editor.colorize(text, language, {});
      const tokens = monaco.editor.tokenize(text, language);
      if (current) setLines(text.split('\n').map((line, index) => tokenSegments(line, tokens[index] || [])));
    }).catch(() => { /* Plaintext preserves content when tokenization fails. */ });
    return () => { current = false; };
  }, [text, language]);
  const label = language === 'network-config' ? 'Network CLI' : language === 'plaintext' ? fence || 'Text' : language === 'jinja2' ? 'Jinja2' : language;
  return <div className="assistant-code"><div className="assistant-code-bar"><span>{label}</span><CopyAction content={text} /></div><pre><code>{lines.length ? lines.map((segments, index) => <span className="assistant-code-line" key={index}>{segments.map((segment, part) => <span key={part} className={segment.className}>{segment.text}</span>)}{index < lines.length - 1 ? '\n' : ''}</span>) : text}</code></pre></div>;
}

/** Shared, theme-aware prose for both assistants. Raw HTML is never rendered. */
export default function AssistantMarkdown({ content, onOpenFile, copyable = false }: { content: string; onOpenFile?: (path: string) => void; copyable?: boolean }) {
  return <><div className="assistant-prose"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
    table: ({ children }) => <div className="assistant-table"><table>{children}</table></div>,
    a: ({ href, children }) => {
      const file = href && !/^[a-z]+:/i.test(href) && !href.startsWith('//') && /\.(yml|yaml|json|j2|txt|cfg|conf|py|md)(?:#.*)?$/i.test(href);
      return file && onOpenFile ? <button className="link link-primary" onClick={() => onOpenFile(href!)}>{children}</button> : <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
    },
  }}>{content}</ReactMarkdown></div>{copyable && <CopyResponse content={content} />}</>;
}

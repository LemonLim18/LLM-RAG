import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy } from 'lucide-react';

function CodeBlock({ children }: { children: any }) {
  const [copied, setCopied] = useState(false);
  const text = String(children?.props?.children ?? '').replace(/\n$/, '');
  const language = String(children?.props?.className || '').replace('language-', '') || 'text';
  return <div className="assistant-code"><div className="assistant-code-bar"><span>{language}</span><button aria-label="Copy code" onClick={() => void navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1600); })}>{copied ? <Check size={13} /> : <Copy size={13} />}{copied ? 'Copied' : 'Copy'}</button></div><pre><code>{text}</code></pre></div>;
}

/** Shared, theme-aware prose for both assistants. Raw HTML is never rendered. */
export default function AssistantMarkdown({ content, onOpenFile }: { content: string; onOpenFile?: (path: string) => void }) {
  return <div className="assistant-prose"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
    table: ({ children }) => <div className="assistant-table"><table>{children}</table></div>,
    a: ({ href, children }) => {
      const file = href && !/^[a-z]+:/i.test(href) && !href.startsWith('//') && /\.(yml|yaml|json|j2|txt|cfg|conf|py|md)(?:#.*)?$/i.test(href);
      return file && onOpenFile ? <button className="link link-primary" onClick={() => onOpenFile(href!)}>{children}</button> : <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
    },
  }}>{content}</ReactMarkdown></div>;
}

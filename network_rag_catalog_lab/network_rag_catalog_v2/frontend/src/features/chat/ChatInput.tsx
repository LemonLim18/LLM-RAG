import { Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  local?: boolean;
  disabled?: boolean;
  editing?: boolean;
}

export function ChatInput({ onSend, local = false, disabled = false, editing = false }: ChatInputProps) {
  const [text, setText] = useState('');
  const [composing, setComposing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = `${Math.min(element.scrollHeight, 128)}px`;
  }, [text]);

  const submit = () => {
    const message = text.trim();
    if (!message || composing || disabled) return;
    onSend(message);
    setText('');
  };

  return (
    <div className="chat-composer">
      <label htmlFor="copilot-prompt" className="sr-only">{editing ? 'Instruct Local V9 to edit active file' : local ? 'Request a Local V9 plan' : 'Message the demo Copilot'}</label>
      <textarea
        id="copilot-prompt"
        ref={textareaRef}
        value={text}
        rows={1}
        placeholder={editing ? 'Describe one change to the active working file…' : local ? 'Describe a network configuration preview…' : 'Ask the demo Copilot…'}
        disabled={disabled}
        maxLength={editing ? 2000 : 8000}
        onChange={(event) => setText(event.target.value)}
        onCompositionStart={() => setComposing(true)}
        onCompositionEnd={() => setComposing(false)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey && !composing) {
            event.preventDefault();
            submit();
          }
        }}
      />
      <button type="button" className="icon-button icon-button--accent" aria-label={editing ? 'Propose edit with Local V9' : local ? 'Create Local V9 session' : 'Send demo message'} onClick={submit} disabled={disabled || !text.trim()}>
        <Send size={15} />
      </button>
    </div>
  );
}

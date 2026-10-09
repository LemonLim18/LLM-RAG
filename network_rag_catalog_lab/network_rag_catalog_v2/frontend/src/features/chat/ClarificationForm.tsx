import { useState } from 'react';
import type { AnswerValue, ClarificationQuestion } from '../../services/planningApi';

interface Props {
  question: ClarificationQuestion;
  disabled: boolean;
  onAnswer: (answer: AnswerValue) => void;
}

export function ClarificationForm({ question, disabled, onAnswer }: Props) {
  const [kind, setKind] = useState<'selection' | 'custom'>(question.options.length ? 'selection' : 'custom');
  const [selected, setSelected] = useState<string[]>([]);
  const [text, setText] = useState('');
  const unsupported = !question.options.length && !question.allow_custom;
  return (
    <form className="clarification-form" aria-label="Answer current V9 question" onSubmit={(event) => {
      event.preventDefault();
      if (disabled || unsupported || (kind === 'selection' ? !selected.length : !text.trim())) return;
      onAnswer({ question_id: question.question_id, revision: question.revision, source_revision: question.source_revision,
        kind, raw_input: kind === 'custom' ? text : '', selected_ids: kind === 'selection' ? selected : [] });
    }}>
      <h3>Current question</h3>
      <p>{question.wording}</p>
      <p className="planning-id">Question: {question.question_id} · Task: {question.task_id}</p>
      <fieldset disabled={disabled || unsupported}>
        <legend>{question.field_path}</legend>
        {question.options.length > 0 && question.allow_custom && <label>Answer method
          <select aria-label="Answer method" value={kind} onChange={(event) => setKind(event.target.value as 'selection' | 'custom')}>
            <option value="selection">Select listed option{question.multiple ? 's' : ''}</option>
            <option value="custom">Enter a value</option>
          </select>
        </label>}
        {kind === 'selection' && question.options.map((option) => (
          <label className="clarification-option" key={option.option_id}>
            <input type={question.multiple ? 'checkbox' : 'radio'} name="v9-option" value={option.option_id}
              checked={selected.includes(option.option_id)} onChange={(event) => setSelected(question.multiple
                ? event.target.checked ? [...selected, option.option_id] : selected.filter((id) => id !== option.option_id)
                : [option.option_id])} />
            <span>{option.label}<small>{option.explanation}</small></span>
          </label>
        ))}
        {kind === 'custom' && question.allow_custom && <label>Answer value
          <textarea aria-label="Answer value" value={text} maxLength={8000} rows={2} onChange={(event) => setText(event.target.value)} />
          <small>Enter a literal value{['array', 'object'].includes(String(question.expected_schema?.type)) ? ' (JSON for structured data)' : ''}. V9 validates it; numbers are never option positions.</small>
        </label>}
        {unsupported && <p>This question has no supported answer control. No answer will be substituted.</p>}
        <button type="submit" disabled={kind === 'selection' ? !selected.length : !text.trim()}>Submit answer to V9</button>
      </fieldset>
    </form>
  );
}

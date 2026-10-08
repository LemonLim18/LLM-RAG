import { Activity, ChevronDown, CircleDot, TerminalSquare } from 'lucide-react';
import { useState } from 'react';
import { useWorkbench } from '../../app/workbenchContext';

type ActivityTab = 'activity' | 'output';

export function ActivityPanel() {
  const { state, dispatch } = useWorkbench();
  const [tab, setTab] = useState<ActivityTab>('activity');
  const recent = [...state.activity].reverse();

  return (
    <section className="activity-panel" aria-label="Simulated activity and output">
      <div className="activity-tabs" role="tablist" aria-label="Bottom panel views">
        <button type="button" role="tab" aria-selected={tab === 'activity'} className={tab === 'activity' ? 'is-active' : ''} onClick={() => setTab('activity')}><Activity size={13} /> ACTIVITY <span>{state.activity.length}</span></button>
        <button type="button" role="tab" aria-selected={tab === 'output'} className={tab === 'output' ? 'is-active' : ''} onClick={() => setTab('output')}><TerminalSquare size={13} /> OUTPUT</button>
        <span className="activity-spacer" />
        <span className="simulated-label"><CircleDot size={12} /> SIMULATED</span>
        <button type="button" className="icon-button" aria-label="Hide activity panel" onClick={() => dispatch({ type: 'TOGGLE_PANEL', panel: 'activity' })}><ChevronDown size={15} /></button>
      </div>
      {tab === 'activity' ? (
        <div className="activity-list" role="tabpanel">
          {recent.map((entry) => (
            <div className="activity-row" key={entry.id}>
              <span className={`activity-kind activity-kind--${entry.kind}`}>{entry.kind}</span>
              <span className="activity-time">{entry.createdAt}</span>
              <span>{entry.message}</span>
              <span className="demo-tag">SIMULATED</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="output-console" role="tabpanel" aria-label="Demo output">
          <span className="console-muted">[demo]</span> Frontend shell is running locally.\n
          <span className="console-muted">[demo]</span> Monaco worker loaded from the frontend bundle.\n
          <span className="console-warning">[mock]</span> Backend output is unavailable in Iteration 1.\n
          <span className="console-caret">›</span> Waiting for local UI interaction…
        </div>
      )}
    </section>
  );
}

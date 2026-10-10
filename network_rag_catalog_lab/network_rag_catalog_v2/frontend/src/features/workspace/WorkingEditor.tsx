import { useEffect, useState } from 'react';
import { useWorkbench } from '../../app/workbenchContext';
import { WorkingTextEditor } from './WorkingTextEditor';
import { InlineChangeReview } from './InlineChangeReview';

export function WorkingEditor() {
  const { working } = useWorkbench();
  return working.tabs[working.activeId] ? <WorkingDocumentEditor key={working.activeId} /> : <p className="empty-state">Select a Working File from Explorer.</p>;
}

function WorkingDocumentEditor() {
  const { working } = useWorkbench();
  const id = working.activeId;
  const tab = working.tabs[id];
  const [manualReview, setManualReview] = useState(false);
  const reviewing = Boolean(tab.proposal) || manualReview;
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === 's') {
        event.preventDefault(); event.stopPropagation(); if (!reviewing) void working.save(id);
      }
    };
    window.addEventListener('keydown', shortcut, true);
    return () => window.removeEventListener('keydown', shortcut, true);
  }, [working, id, reviewing]);
  const original = tab.saved.original;
  const dirty = tab.content !== tab.saved.content;
  const proposal = tab.proposal;
  return <section className="generated-editor working-editor" aria-label="Editable working document">
    <div className="working-tabs" role="tablist" aria-label="Open working files">
      {Object.entries(working.tabs).map(([key, item]) => <button type="button" role="tab" aria-selected={key === id} key={key}
        title={`${item.saved.original.source.task_id} · ${key}`}
        onClick={() => void working.open(key)}>{item.saved.original.hostname ?? item.saved.original.source.device_id} · {item.saved.original.operation_id} · {item.saved.original.source.config_index + 1} · {key.slice(-8)}{item.content !== item.saved.content ? ' ●' : ''}</button>)}
    </div>
    <header className="generated-editor__provenance">
      <div><strong>Working file · {original.hostname ?? original.source.device_id} · {original.operation_id}</strong>
        <div className="working-editor-actions">
          <button type="button" disabled={Boolean(proposal) || tab.saving} onClick={() => setManualReview((old) => !old)}>{manualReview ? 'Close Review' : 'Review Changes'}</button>
          <button type="button" disabled={tab.saving || tab.blocked || reviewing} onClick={() => void working.save(id)}>{tab.saving ? 'Saving…' : 'Save (Ctrl+S)'}</button>
        </div></div>
      <p role="status">{dirty ? 'Unsaved changes' : 'Saved working content'} · UNVALIDATED · not deployed</p>
      <small>Historical source · current validity not checked. Original remains unchanged. Unsaved edits are lost on browser reload.</small>
      {proposal ? <section className="proposal-toolbar" aria-label="Pending change proposal">
        <strong>{proposal.status === 'stale' ? 'Stale proposal — acceptance blocked' : 'Pending proposal — not applied'}</strong>
        <p>Source: {proposal.source} · Proposal {proposal.proposalId}</p>
        {proposal.description && <p>{proposal.description}</p>}
        <p>Whole-proposal review · no automatic save, validation or deployment.</p>
        {proposal.reason && <p role="alert">{proposal.reason}</p>}
        <button type="button" disabled={proposal.status !== 'pending' || tab.saving || tab.blocked} onClick={() => { working.acceptProposal(id, proposal.proposalId); setManualReview(false); }}>Accept Changes</button>
        <button type="button" onClick={() => { working.rejectProposal(id, proposal.proposalId); setManualReview(false); }}>Reject Changes</button>
      </section> : manualReview && <p className="manual-review-notice">Manual edits compared with the last confirmed saved working text, not the immutable original. Close Review to keep editing; nothing is accepted or saved here.</p>}
      {tab.reviewMessage && <p role="status">{tab.reviewMessage}</p>}
      <details><summary>Working identity and source</summary><dl>
        <dt>Document</dt><dd>{id}</dd><dt>Revision</dt><dd>{tab.saved.revision}</dd>
        <dt>Original</dt><dd>{original.artifact_id}</dd><dt>Session</dt><dd>{original.source.session_id}</dd>
        <dt>Source revision</dt><dd>{original.source.session_revision}</dd><dt>Task</dt><dd>{original.source.task_id}</dd>
        <dt>Device</dt><dd>{original.source.device_id}</dd><dt>Vendor/platform</dt><dd>{original.vendor} / {original.platform}</dd>
      </dl></details>
      {tab.error && <div role="alert"><p>{tab.error}</p><p>Local text retained; save blocked until you inspect and explicitly reconcile saved state.</p>
        <button type="button" onClick={() => void working.inspect(id)}>Inspect saved state</button></div>}
      {tab.inspected && <div className="working-inspection"><p>Observed saved revision: {tab.inspected.revision}. {tab.inspected.content === tab.content ? 'Saved text matches local text.' : 'Saved text differs from local text.'} This does not identify which request wrote it.</p>
        <details><summary>Inspect saved text (read-only)</summary><pre>{tab.inspected.content}</pre></details>
        <button type="button" onClick={() => working.acceptInspection(id, false)}>Use latest revision, keep my text</button>
        <button type="button" onClick={() => { if (window.confirm('Discard local edits and load the inspected saved text?')) working.acceptInspection(id, true); }}>Discard local edits and load saved</button>
      </div>}
    </header>
    <div className="monaco-host working-editor-surface">
      <WorkingTextEditor id={id} content={tab.content} reviewing={reviewing} />
      {reviewing && <InlineChangeReview key={proposal ? `proposal-${proposal.proposalId}` : `manual-${tab.saved.revision}-${tab.bufferEpoch}`}
        documentId={id} reviewId={proposal ? `proposal-${proposal.proposalId}` : `manual-${tab.saved.revision}-${tab.bufferEpoch}`}
        base={proposal?.baseContent ?? tab.saved.content} proposed={proposal?.proposedContent ?? tab.content} />}
    </div>
  </section>;
}

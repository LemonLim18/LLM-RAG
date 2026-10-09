import { useState } from 'react';
import { useWorkbench } from '../../app/workbenchContext';

export function SessionRecovery() {
  const { localPlanning } = useWorkbench();
  const { recovery, recoveryMetadata, busy } = localPlanning;
  const [enteredId, setEnteredId] = useState<string | null>(null);
  const id = enteredId ?? recoveryMetadata.reference?.sessionId ?? '';
  return <section className="session-recovery" aria-label="Saved session recovery">
    <h3>Restore a known session</h3>
    <p>Read the saved state without refreshing or replaying an operation.</p>
    <form onSubmit={(event) => { event.preventDefault(); localPlanning.restore(id); }}>
      <label>Saved session ID<input aria-label="Saved session ID" value={id} disabled={busy}
        onChange={(event) => setEnteredId(event.target.value)} placeholder="Session UUID" /></label>
      <div className="recovery-actions">
        <button type="submit" disabled={busy || !id.trim()}>Restore saved session</button>
        <button type="button" disabled={busy || !recoveryMetadata.reference} onClick={() => {
          localPlanning.clearRecoveryReference(); setEnteredId('');
        }}>Clear recovery reference</button>
      </div>
    </form>
    {localPlanning.state.result && <button type="button" disabled={busy}
      onClick={() => localPlanning.restore(localPlanning.state.result!.session.session_id)}>Read latest saved state</button>}
    {recoveryMetadata.reference && <p className="planning-id">Remembered session: {recoveryMetadata.reference.sessionId}</p>}
    {localPlanning.storageWarning && <p role="alert">{localPlanning.storageWarning}</p>}
    {recovery.message && <p role={recovery.phase === 'error' || recovery.uncertain ? 'alert' : 'status'}>{recovery.message}</p>}
    {recoveryMetadata.unknownCreationRequestId && <div>
      <p role="note">
      Unconfirmed creation request: <code>{recoveryMetadata.unknownCreationRequestId}</code>.
      Its session ID was not confirmed. Check the durable receipt without replaying creation.
      A remembered older session is unrelated. An unknown or indeterminate outcome is not permission to retry.
      </p>
      <button type="button" disabled={busy} onClick={localPlanning.checkCreationOutcome}>Check creation outcome</button>
    </div>}
    {localPlanning.creationRecovery.message && <div
      role={localPlanning.creationRecovery.phase === 'error' || ['indeterminate', 'corrupt', 'terminal_error'].includes(localPlanning.creationRecovery.outcome?.status ?? '') ? 'alert' : 'status'}>
      {localPlanning.creationRecovery.outcome && <strong>Creation outcome: {localPlanning.creationRecovery.outcome.status}</strong>}
      <p>{localPlanning.creationRecovery.message}</p>
    </div>}
  </section>;
}

import { useWorkbench } from '../../app/workbenchContext';

export function SavedOriginals() {
  const { state, dispatch, originals } = useWorkbench();
  const { collection, opened } = originals;
  return <section className="saved-originals" aria-label="Saved Originals">
    <div className="saved-originals__heading"><div><small>CONFIGURATIONS</small><h3>Saved Originals</h3></div>
      <button type="button" aria-label="Refresh Saved Originals" disabled={collection.phase === 'loading'} onClick={() => void originals.refresh()}>Refresh</button></div>
    <small>Immutable V9 snapshots · not deployed</small>
    <div className="saved-originals__list">
      {collection.phase === 'loading' && <p role="status">Loading saved originals…</p>}
      {collection.phase === 'error' && <p role="alert">{collection.error}</p>}
      {collection.phase === 'ready' && collection.items.length === 0 && <p>No saved originals. Open a V9 preview and choose Save to Workspace.</p>}
      {collection.items.map((item) => <button key={item.artifact_id} type="button"
        className="saved-originals__row" aria-current={state.workspaceView === 'original' && opened.id === item.artifact_id ? 'true' : undefined}
        aria-label={`Open saved original ${item.hostname ?? item.source.device_id} ${item.operation_id ?? 'operation not reported'} ${item.source.task_id} output ${item.source.config_index + 1} ${item.artifact_id}`}
        onClick={() => { dispatch({ type: 'SHOW_WORKSPACE_VIEW', view: 'original' }); void originals.open(item.artifact_id); }}>
        <strong>{item.hostname ?? item.source.device_id} · {item.operation_id ?? 'Operation not reported'}</strong>
        <span>{item.source.task_id} · Output {item.source.config_index + 1}</span>
        <small>{item.captured_at} · {item.artifact_id.slice(-8)}</small>
      </button>)}
    </div>
  </section>;
}

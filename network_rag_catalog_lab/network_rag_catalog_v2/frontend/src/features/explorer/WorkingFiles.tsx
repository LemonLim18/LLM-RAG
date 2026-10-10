import { useWorkbench } from '../../app/workbenchContext';

export function WorkingFiles() {
  const { working, state } = useWorkbench();
  return <section className="saved-originals working-files" aria-label="Working Files">
    <div className="saved-originals__heading"><div><small>CONFIGURATIONS</small><h3>Working Files</h3></div>
      <button type="button" aria-label="Refresh Working Files" disabled={working.collection.loading} onClick={() => void working.refresh()}>Refresh</button></div>
    <small>Editable · unvalidated · no deployment</small>
    <div className="saved-originals__list">
      {working.collection.loading && <p role="status">Loading working files…</p>}
      {working.collection.error && <p role="alert">{working.collection.error}</p>}
      {!working.collection.loading && !working.collection.items.length && <p>No working files. Open generated output in Editor.</p>}
      {working.collection.items.map((item) => <button type="button" className="saved-originals__row" key={item.document_id}
        aria-current={state.workspaceView === 'working' && working.activeId === item.document_id ? 'true' : undefined}
        aria-label={`Open working file ${item.original.hostname ?? item.original.source.device_id} ${item.original.operation_id} ${item.original.source.task_id} output ${item.original.source.config_index + 1}`}
        onClick={() => void working.open(item.document_id)}>
        <strong>{item.original.hostname ?? item.original.source.device_id} · {item.original.operation_id}</strong>
        <span>{item.original.source.task_id} · Output {item.original.source.config_index + 1}</span>
        <small>{item.document_id.slice(-8)} · saved {item.updated_at}</small>
      </button>)}
    </div>
    {working.opening.message && <p role="status">{working.opening.message}</p>}
  </section>;
}

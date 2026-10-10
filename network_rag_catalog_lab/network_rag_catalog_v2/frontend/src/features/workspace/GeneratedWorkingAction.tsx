import { useWorkbench } from '../../app/workbenchContext';
import type { PlanningTask, SessionSnapshot } from '../../services/planningApi';
import { deviceConfiguration } from './generatedPreview';

export function GeneratedWorkingAction({ result, task, index, label = 'Open in Editor' }: {
  result: SessionSnapshot; task: PlanningTask; index: number; label?: string;
}) {
  const { working } = useWorkbench();
  const config = deviceConfiguration(task, index);
  if (!config) return null;
  return <button type="button" disabled={working.opening.pending} onClick={() => void working.prepare({
    sessionId: result.session.session_id, sessionRevision: result.session_revision,
    taskId: task.intent_id, deviceId: config.device_id, configIndex: index,
  })}>{label} · {config.device_id} · output {index + 1}</button>;
}

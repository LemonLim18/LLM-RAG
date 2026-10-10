import type { GeneratedPreviewSelection } from '../../app/types';
import type { Json, PlanningTask, SessionSnapshot } from '../../services/planningApi';

// configs are nested under their task; never search other tasks or infer a device
// from hostname, list position, the explorer selection or a sample document.
export function deviceConfiguration(task: PlanningTask, index: number) {
  const config = task.configs[index];
  if (!config || typeof config.configuration !== 'string' || !config.configuration.length
      || typeof config.device_id !== 'string' || !config.device_id
      || !task.target_devices.some((device) => device.id === config.device_id)
      || (task.device_id && task.device_id !== config.device_id)) return null;
  return config as Record<string, Json> & { device_id: string; configuration: string };
}

export function resolveGeneratedPreview(result: SessionSnapshot | undefined, selection: GeneratedPreviewSelection | null) {
  if (!result || !selection || result.session.session_id !== selection.sessionId
      || result.session_revision !== selection.sessionRevision) return null;
  const task = result.session.plan.tasks.find((item) => item.intent_id === selection.taskId);
  if (!task) return null;
  const config = deviceConfiguration(task, selection.configIndex);
  if (!config || config.device_id !== selection.deviceId) return null;
  return { task, config };
}

export function previewModelPath(selection: GeneratedPreviewSelection) {
  // Entry index is scoped to a saved snapshot, not a persistent artifact ID.
  return `inmemory://v9-preview/${encodeURIComponent(JSON.stringify([
    selection.sessionId, selection.sessionRevision, selection.taskId, selection.deviceId, selection.configIndex,
  ]))}/configuration`;
}

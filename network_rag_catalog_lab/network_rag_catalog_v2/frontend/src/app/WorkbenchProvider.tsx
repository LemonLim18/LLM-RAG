import { useCallback, useEffect, useReducer, useRef, useState, type ReactNode } from 'react';
import { readInventory } from '../services/inventoryApi';
import { BackendResponseError } from '../services/runtimeApi';
import { initialWorkbenchState, workbenchReducer } from './workbenchReducer';
import { WorkbenchContext } from './workbenchContext';
import { useLocalPlanning } from '../features/chat/useLocalPlanning';
import { useSavedOriginals } from '../features/workspace/useSavedOriginals';
import { useWorkingDocuments } from '../features/workspace/useWorkingDocuments';
import { deviceConfiguration } from '../features/workspace/generatedPreview';
import type { WorkbenchAction } from './types';

export function WorkbenchProvider({ children }: { children: ReactNode }) {
  const [state, reduce] = useReducer(workbenchReducer, initialWorkbenchState);
  const [inventoryAttempt, setInventoryAttempt] = useState(0);
  const inventoryRead = useRef(0);
  const originals = useSavedOriginals();
  const working = useWorkingDocuments(() => reduce({ type: 'SHOW_WORKSPACE_VIEW', view: 'working' }), () => void originals.refresh(), state.workspaceView === 'working');
  const dispatch = (action: WorkbenchAction) => {
    if (['SHOW_WORKSPACE_VIEW', 'OPEN_GENERATED_PREVIEW', 'ACTIVATE_TAB', 'SELECT_DEVICE', 'CLOSE_GENERATED_PREVIEW'].includes(action.type)) working.cancelFocus();
    if (action.type === 'SHOW_WORKSPACE_VIEW' && action.view === 'working') working.allowFocus();
    reduce(action);
  };
  const localPlanning = useLocalPlanning((result) => {
    working.cancelFocus();
    const tasks = result.session.plan.tasks;
    if (result.session.status !== 'ready' || result.session.pending_questions.length || tasks.length !== 1 || tasks[0].configs.length !== 1) return;
    const config = deviceConfiguration(tasks[0], 0);
    if (!config || tasks[0].target_devices.filter((device) => device.id === config.device_id).length !== 1) return;
    void working.prepare({ sessionId: result.session.session_id, sessionRevision: result.session_revision,
      taskId: tasks[0].intent_id, deviceId: config.device_id, configIndex: 0 });
  });
  const planningResult = localPlanning.state.result;

  useEffect(() => {
    if (!planningResult) return;
    reduce({
      type: 'SYNC_PLANNING_SESSION',
      sessionId: planningResult.session.session_id,
      sessionRevision: planningResult.session_revision,
      taskIds: planningResult.session.plan.tasks.map((task) => task.intent_id),
    });
  }, [planningResult]);

  useEffect(() => {
    const attempt = ++inventoryRead.current;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort('timeout'), 5_000);
    readInventory(controller.signal)
      .then((response) => { if (attempt === inventoryRead.current) reduce({
        type: 'INVENTORY_LOADED',
        devices: response.devices,
        source: response.source,
        revision: response.inventory_revision,
      }); })
      .catch((error: unknown) => {
        if (attempt !== inventoryRead.current || (controller.signal.aborted && controller.signal.reason !== 'timeout')) return;
        const message = error instanceof BackendResponseError
          ? `Inventory API error (HTTP ${error.status}).`
          : 'V9 demo inventory is unavailable.';
        reduce({ type: 'INVENTORY_FAILED', message });
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      window.clearTimeout(timeout);
      controller.abort('unmounted');
    };
  }, [inventoryAttempt]);

  const refreshInventory = useCallback(async (selectDeviceId?: string) => {
    const attempt = ++inventoryRead.current;
    const response = await readInventory(AbortSignal.timeout(5_000));
    if (attempt === inventoryRead.current) reduce({ type: 'INVENTORY_LOADED', devices: response.devices,
      source: response.source, revision: response.inventory_revision, selectDeviceId });
    return response;
  }, []);

  const retryInventory = useCallback(() => {
    reduce({ type: 'INVENTORY_LOADING' });
    setInventoryAttempt((current) => current + 1);
  }, []);
  const value = { state, dispatch, retryInventory, refreshInventory, localPlanning, originals, working };
  return <WorkbenchContext.Provider value={value}>{children}</WorkbenchContext.Provider>;
}

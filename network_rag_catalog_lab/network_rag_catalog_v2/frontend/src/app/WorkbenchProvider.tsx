import { useCallback, useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from 'react';
import { readInventory } from '../services/inventoryApi';
import { BackendResponseError } from '../services/runtimeApi';
import { initialWorkbenchState, workbenchReducer } from './workbenchReducer';
import { WorkbenchContext } from './workbenchContext';
import { useLocalPlanning } from '../features/chat/useLocalPlanning';

export function WorkbenchProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(workbenchReducer, initialWorkbenchState);
  const [inventoryAttempt, setInventoryAttempt] = useState(0);
  const inventoryRead = useRef(0);
  const localPlanning = useLocalPlanning();
  const planningResult = localPlanning.state.result;

  useEffect(() => {
    if (!planningResult) return;
    dispatch({
      type: 'SYNC_PLANNING_SESSION',
      sessionId: planningResult.session.session_id,
      taskIds: planningResult.session.plan.tasks.map((task) => task.intent_id),
    });
  }, [planningResult]);

  useEffect(() => {
    const attempt = ++inventoryRead.current;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort('timeout'), 5_000);
    readInventory(controller.signal)
      .then((response) => { if (attempt === inventoryRead.current) dispatch({
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
        dispatch({ type: 'INVENTORY_FAILED', message });
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
    if (attempt === inventoryRead.current) dispatch({ type: 'INVENTORY_LOADED', devices: response.devices,
      source: response.source, revision: response.inventory_revision, selectDeviceId });
    return response;
  }, []);

  const retryInventory = useCallback(() => {
    dispatch({ type: 'INVENTORY_LOADING' });
    setInventoryAttempt((current) => current + 1);
  }, []);
  const value = useMemo(() => ({ state, dispatch, retryInventory, refreshInventory, localPlanning }), [state, retryInventory, refreshInventory, localPlanning]);
  return <WorkbenchContext.Provider value={value}>{children}</WorkbenchContext.Provider>;
}

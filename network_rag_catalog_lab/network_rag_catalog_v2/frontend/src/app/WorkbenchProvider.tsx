import { useCallback, useEffect, useMemo, useReducer, useState, type ReactNode } from 'react';
import { readInventory } from '../services/inventoryApi';
import { BackendResponseError } from '../services/runtimeApi';
import { initialWorkbenchState, workbenchReducer } from './workbenchReducer';
import { WorkbenchContext } from './workbenchContext';
import { useLocalPlanning } from '../features/chat/useLocalPlanning';

export function WorkbenchProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(workbenchReducer, initialWorkbenchState);
  const [inventoryAttempt, setInventoryAttempt] = useState(0);
  const localPlanning = useLocalPlanning();

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort('timeout'), 5_000);
    readInventory(controller.signal)
      .then((response) => dispatch({
        type: 'INVENTORY_LOADED',
        devices: response.devices,
        source: response.source,
        revision: response.inventory_revision,
      }))
      .catch((error: unknown) => {
        if (controller.signal.aborted && controller.signal.reason !== 'timeout') return;
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

  const retryInventory = useCallback(() => {
    dispatch({ type: 'INVENTORY_LOADING' });
    setInventoryAttempt((current) => current + 1);
  }, []);
  const value = useMemo(() => ({ state, dispatch, retryInventory, localPlanning }), [state, retryInventory, localPlanning]);
  return <WorkbenchContext.Provider value={value}>{children}</WorkbenchContext.Provider>;
}

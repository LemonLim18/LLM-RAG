import { useRef, useState } from 'react';
import { createPlanningSession, type PlanningRequest, type PlanningResponse } from '../../services/planningApi';

export interface LocalPlanningState {
  phase: 'idle' | 'pending' | 'success' | 'error';
  request?: PlanningRequest;
  result?: PlanningResponse;
  error?: string;
}

export function useLocalPlanning() {
  const [state, setState] = useState<LocalPlanningState>({ phase: 'idle' });
  const pending = useRef(false);
  const send = async (request: PlanningRequest) => {
    if (pending.current) return;
    pending.current = true;
    setState({ phase: 'pending', request });
    try {
      const result = await createPlanningSession(request);
      setState({ phase: 'success', request, result });
    } catch (error) {
      setState({ phase: 'error', request, error: error instanceof Error ? error.message : 'Unexpected response from V9.' });
    } finally {
      pending.current = false;
    }
  };
  return {
    state,
    submit: (prompt: string) => { void send({ prompt, mode: 'local_v9', client_request_id: crypto.randomUUID() }); },
    retry: () => { if (state.request) void send(state.request); },
    reset: () => { if (!pending.current) setState({ phase: 'idle' }); },
  };
}

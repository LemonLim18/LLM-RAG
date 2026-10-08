import { useCallback, useEffect, useState } from 'react';
import { BackendResponseError, readBackendSnapshot, type BackendSnapshot } from '../../services/runtimeApi';

export type BackendConnection =
  | { phase: 'loading'; snapshot: null; message: string }
  | { phase: 'connected'; snapshot: BackendSnapshot; message: string }
  | { phase: 'disconnected'; snapshot: null; message: string }
  | { phase: 'error'; snapshot: null; message: string };

export function useBackendStatus() {
  const [attempt, setAttempt] = useState(0);
  const [connection, setConnection] = useState<BackendConnection>({
    phase: 'loading',
    snapshot: null,
    message: 'Checking backend…',
  });

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort('timeout'), 5_000);
    readBackendSnapshot(controller.signal)
      .then((snapshot) => setConnection({ phase: 'connected', snapshot, message: 'Backend connected' }))
      .catch((error: unknown) => {
        if (controller.signal.aborted && controller.signal.reason !== 'timeout') return;
        if (error instanceof BackendResponseError) {
          setConnection({ phase: 'error', snapshot: null, message: `Backend error (HTTP ${error.status})` });
          return;
        }
        setConnection({ phase: 'disconnected', snapshot: null, message: 'Backend unavailable' });
      })
      .finally(() => window.clearTimeout(timeout));

    return () => {
      window.clearTimeout(timeout);
      controller.abort('unmounted');
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setConnection({ phase: 'loading', snapshot: null, message: 'Checking backend…' });
    setAttempt((current) => current + 1);
  }, []);
  return { connection, retry };
}

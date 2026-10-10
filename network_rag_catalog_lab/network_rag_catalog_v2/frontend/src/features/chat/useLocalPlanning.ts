import { useRef, useState } from 'react';
import { AnswerError, createPlanningSession, readCreationOutcome, readSavedSession, submitClarification, type AnswerRequest, type AnswerValue, type CreationOutcome, type PlanningRequest, type SessionSnapshot } from '../../services/planningApi';
import { isSessionId, readRecoveryMetadata, recordedAnswerOutcome, saveRecoveryMetadata, type RecoveryMetadata } from './recoveryMetadata';

export interface AnswerState {
  phase: 'idle' | 'pending' | 'success' | 'error';
  request?: AnswerRequest;
  sessionId?: string;
  error?: AnswerError;
}

export interface LocalPlanningState {
  phase: 'idle' | 'pending' | 'success' | 'error';
  request?: PlanningRequest;
  result?: SessionSnapshot;
  historical?: boolean;
  error?: string;
}

export function useLocalPlanning(onConfirmed?: (result: SessionSnapshot) => void) {
  const [state, setState] = useState<LocalPlanningState>({ phase: 'idle' });
  const pending = useRef(false);
  const [answerState, setAnswerState] = useState<AnswerState>({ phase: 'idle' });
  const [recoveryMetadata, setRecoveryMetadata] = useState(readRecoveryMetadata);
  const metadataRef = useRef(recoveryMetadata);
  const [storageWarning, setStorageWarning] = useState('');
  const [creationRecovery, setCreationRecovery] = useState<{ phase: 'idle' | 'pending' | 'success' | 'error'; outcome?: CreationOutcome; message?: string }>({ phase: 'idle' });
  const [recovery, setRecovery] = useState<{ phase: 'idle' | 'pending' | 'success' | 'error'; message: string; uncertain: boolean }>({ phase: 'idle', message: '', uncertain: false });
  const remember = (data: RecoveryMetadata) => {
    metadataRef.current = data;
    setRecoveryMetadata(data);
    setStorageWarning(saveRecoveryMetadata(data) ? '' : 'Browser storage is unavailable. Keep the session ID to restore it manually.');
  };
  const rememberSession = (result: SessionSnapshot, answerUncertain = false) => remember({ ...metadataRef.current,
    reference: { sessionId: result.session.session_id, revision: result.session_revision, answerUncertain } });
  const send = async (request: PlanningRequest) => {
    if (pending.current) return;
    pending.current = true;
    remember({ ...metadataRef.current, unknownCreationRequestId: request.client_request_id });
    setCreationRecovery({ phase: 'idle' });
    setRecovery({ phase: 'idle', message: '', uncertain: false });
    setAnswerState({ phase: 'idle' });
    setState({ phase: 'pending', request });
    try {
      const result = await createPlanningSession(request);
      setState({ phase: 'success', request, result });
      remember({ reference: { sessionId: result.session.session_id, revision: result.session_revision, answerUncertain: false } });
      onConfirmed?.(result);
    } catch (error) {
      setState({ phase: 'error', request, error: error instanceof Error ? error.message : 'Unexpected response from V9.' });
    } finally {
      pending.current = false;
    }
  };
  const sendAnswer = async (sessionId: string, request: AnswerRequest) => {
    if (pending.current) return;
    pending.current = true;
    setRecovery({ phase: 'idle', message: '', uncertain: false });
    if (state.result) rememberSession(state.result, true);
    setAnswerState({ phase: 'pending', request, sessionId });
    try {
      const result = await submitClarification(sessionId, request);
      setState((prior) => ({ ...prior, result, historical: false }));
      rememberSession(result);
      setAnswerState({ phase: 'success', request, sessionId });
      onConfirmed?.(result);
    } catch (caught) {
      const error = caught instanceof AnswerError ? caught : new AnswerError('OUTCOME_UNKNOWN', 'Answer outcome unknown.');
      if (error.currentSession?.session.session_id === sessionId) {
        setState((prior) => ({ ...prior, result: error.currentSession }));
        rememberSession(error.currentSession);
      }
      setAnswerState({ phase: 'error', request, sessionId, error });
    } finally {
      pending.current = false;
    }
  };
  const restore = async (id: string) => {
    if (pending.current) return;
    const sessionId = id.trim().toLowerCase();
    if (!isSessionId(sessionId)) {
      setRecovery((prior) => ({ ...prior, phase: 'error', message: 'Enter a valid session UUID.' }));
      return;
    }
    pending.current = true;
    setRecovery((prior) => ({ ...prior, phase: 'pending', message: 'Reading saved session…' }));
    try {
      const result = await readSavedSession(sessionId);
      const reference = metadataRef.current.reference?.sessionId === sessionId ? metadataRef.current.reference : undefined;
      const previous = state.result?.session.session_id === sessionId ? state.result : undefined;
      const revision = previous?.session_revision ?? reference?.revision;
      const hadUncertainAnswer = (Boolean(previous) && recovery.uncertain) || reference?.answerUncertain === true
        || (answerState.phase === 'error' && answerState.sessionId === sessionId && !answerState.error?.currentSession);
      const outcome = previous && answerState.request && hadUncertainAnswer
        ? recordedAnswerOutcome(previous, result, answerState.request.answer) : undefined;
      const comparison = revision ? result.session_revision === revision ? 'Saved revision is unchanged.' : 'Saved revision has changed.' : 'No previous revision is available for comparison.';
      const uncertain = hadUncertainAnswer && !outcome;
      setState({ phase: 'success', result, historical: true });
      // A read may precede the worker's save. Retain its answer for a later
      // explicit read, while keeping mutation blocked until evidence arrives.
      if (!uncertain || answerState.sessionId !== sessionId) setAnswerState({ phase: 'idle' });
      rememberSession(result, uncertain);
      setRecovery({ phase: 'success', uncertain, message: `${comparison} ${outcome
        ? `V9 history records this exact answer as ${outcome}. The HTTP request ID is not stored, so its originating request cannot be proven.`
        : uncertain ? 'Answer outcome remains uncertain. A revision change alone does not identify the request. No answer was replayed; further answers are blocked.'
          : 'Saved state restored. Current catalog and inventory validity have not been checked.'}` });
    } catch (error) {
      setRecovery((prior) => ({ ...prior, phase: 'error', message: error instanceof Error ? error.message : 'Saved session could not be read.' }));
    } finally { pending.current = false; }
  };
  const checkCreationOutcome = async () => {
    const requestId = metadataRef.current.unknownCreationRequestId;
    if (pending.current || !requestId) return;
    pending.current = true;
    setCreationRecovery({ phase: 'pending', message: 'Checking recorded creation outcome…' });
    try {
      const outcome = await readCreationOutcome(requestId);
      setCreationRecovery({ phase: 'pending', outcome, message: outcome.message });
      if (outcome.status === 'completed' && outcome.session_id) {
        // The receipt is an association only. Adopt exclusively a validated passive
        // session GET, never an older remembered session or a guessed plan.
        const result = await readSavedSession(outcome.session_id);
        const uncertain = metadataRef.current.reference?.sessionId === result.session.session_id
          && metadataRef.current.reference.answerUncertain;
        setState({ phase: 'success', result, historical: true });
        if (!uncertain) setAnswerState({ phase: 'idle' });
        remember({ reference: { sessionId: result.session.session_id, revision: result.session_revision, answerUncertain: Boolean(uncertain) } });
        setRecovery({ phase: 'success', uncertain: Boolean(uncertain), message: uncertain
          ? 'Recorded creation restored. The prior answer outcome remains uncertain; no answer was replayed.'
          : 'Recorded creation restored as saved historical state. Current catalog and inventory validity have not been checked.' });
      }
      setCreationRecovery({ phase: 'success', outcome, message: outcome.message });
    } catch (error) {
      setCreationRecovery((prior) => ({ ...prior, phase: 'error', message: error instanceof Error ? error.message : 'Unable to check creation outcome.' }));
    } finally { pending.current = false; }
  };
  return {
    state,
    noteInventoryChange: () => setState((prior) => prior.result ? { ...prior, historical: true } : prior),
    answerState,
    recovery, recoveryMetadata, storageWarning, creationRecovery,
    busy: state.phase === 'pending' || answerState.phase === 'pending' || recovery.phase === 'pending' || creationRecovery.phase === 'pending',
    checkCreationOutcome: () => { void checkCreationOutcome(); },
    restore: (id: string) => { void restore(id); },
    clearRecoveryReference: () => { if (!pending.current) remember({ ...metadataRef.current, reference: undefined }); },
    answer: (answer: AnswerValue) => {
      if (!state.result || recovery.uncertain || answerState.phase === 'pending' || answerState.phase === 'error') return;
      void sendAnswer(state.result.session.session_id, {
        client_request_id: crypto.randomUUID(), expected_session_revision: state.result.session_revision, answer,
      });
    },
    retryAnswer: () => { if (answerState.request && answerState.sessionId) void sendAnswer(answerState.sessionId, answerState.request); },
    editAnswer: () => { if (!pending.current) setAnswerState({ phase: 'idle' }); },
    submit: (prompt: string) => { void send({ prompt, mode: 'local_v9', client_request_id: crypto.randomUUID() }); },
    reset: () => { if (!pending.current) { setState({ phase: 'idle' }); setAnswerState({ phase: 'idle' }); } },
  };
}

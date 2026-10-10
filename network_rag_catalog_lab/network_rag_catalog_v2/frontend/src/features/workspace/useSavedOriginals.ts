import { useCallback, useEffect, useRef, useState } from 'react';
import type { GeneratedPreviewSelection } from '../../app/types';
import { captureOriginal, listOriginals, OriginalError, readOriginal, type GeneratedOriginal, type OriginalMetadata } from '../../services/originalsApi';

type Phase = 'idle' | 'loading' | 'ready' | 'error';
const message = (error: unknown) => error instanceof OriginalError ? `${error.code}: ${error.message}` : 'Original storage could not be confirmed.';

// Server response cache, not a second plan or document authority. No browser persistence.
export function useSavedOriginals() {
  const [collection, setCollection] = useState<{ phase: Phase; items: OriginalMetadata[]; error: string }>({ phase: 'loading', items: [], error: '' });
  const [opened, setOpened] = useState<{ phase: Phase; id: string; artifact: GeneratedOriginal | null; error: string }>({ phase: 'idle', id: '', artifact: null, error: '' });
  const [capture, setCapture] = useState<{ phase: Phase; key: string; message: string }>({ phase: 'idle', key: '', message: '' });
  const listSequence = useRef(0);
  const openSequence = useRef(0);
  const capturePending = useRef(false);
  const loadCollection = useCallback(() => {
    const sequence = ++listSequence.current;
    return listOriginals().then((response) => {
      if (sequence === listSequence.current) setCollection({ phase: 'ready', items: response.artifacts, error: '' });
    }).catch((error: unknown) => {
      if (sequence === listSequence.current) setCollection({ phase: 'error', items: [], error: message(error) });
    });
  }, []);
  const refresh = useCallback(() => {
    setCollection((current) => ({ ...current, phase: 'loading', error: '' }));
    return loadCollection();
  }, [loadCollection]);
  useEffect(() => {
    const lists = listSequence, documents = openSequence;
    void loadCollection();
    return () => { ++lists.current; ++documents.current; };
  }, [loadCollection]);
  const open = useCallback(async (id: string) => {
    const sequence = ++openSequence.current;
    setOpened({ phase: 'loading', id, artifact: null, error: '' });
    try {
      const artifact = await readOriginal(id);
      if (artifact.artifact_id !== id || artifact.kind !== 'generated_original' || artifact.schema_version !== 1) {
        throw new OriginalError('INVALID_ORIGINAL_RESPONSE', 'The returned original identity does not match the selected document.');
      }
      if (sequence === openSequence.current) setOpened({ phase: 'ready', id, artifact, error: '' });
    } catch (error) {
      if (sequence === openSequence.current) setOpened({ phase: 'error', id, artifact: null, error: message(error) });
    }
  }, []);
  const save = useCallback(async (selection: GeneratedPreviewSelection) => {
    if (capturePending.current) return;
    capturePending.current = true;
    const key = JSON.stringify(selection);
    setCapture({ phase: 'loading', key, message: 'Saving verified original…' });
    try {
      const response = await captureOriginal(selection);
      setCapture({ phase: 'ready', key, message: response.outcome === 'created'
        ? 'Saved original confirmed. Open it from Saved Originals in Explorer.'
        : 'Already saved — the same original was confirmed; no duplicate created.' });
      await refresh();
    } catch (error) {
      setCapture({ phase: 'error', key, message: message(error) });
    } finally { capturePending.current = false; }
  }, [refresh]);
  return { collection, opened, capture, refresh, open, save };
}

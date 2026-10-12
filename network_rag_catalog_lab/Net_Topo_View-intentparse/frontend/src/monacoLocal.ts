// Serve the existing locked Monaco dependency from Vite; never fetch the CDN.
import { loader } from '@monaco-editor/react';
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api.js';
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker.js?worker';
import 'monaco-editor/esm/vs/basic-languages/yaml/yaml.contribution.js';
import 'monaco-editor/esm/vs/basic-languages/python/python.contribution.js';

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });

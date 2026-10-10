import { defineConfig } from '@playwright/test';
import base from './playwright.config';

// The test owns and restarts only its child backend, against temporary storage.
export default defineConfig({
  ...base,
  testDir: './original-integration',
  timeout: 90_000,
  webServer: [{ command: 'npm run dev -- --host 127.0.0.1', url: 'http://127.0.0.1:5173', reuseExistingServer: false, timeout: 120_000 }],
});

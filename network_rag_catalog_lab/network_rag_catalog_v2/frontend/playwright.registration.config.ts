import { defineConfig } from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testDir: './integration',
  webServer: [
    {
      command: '"..\\..\\.venv\\Scripts\\python.exe" -m tests.workbench_inventory_server',
      cwd: '..', url: 'http://127.0.0.1:8000/api/v1/health', reuseExistingServer: false, timeout: 120_000,
    },
    { command: 'npm run dev -- --host 127.0.0.1', url: 'http://127.0.0.1:5173', reuseExistingServer: false, timeout: 120_000 },
  ],
});

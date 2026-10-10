import { defineConfig } from '@playwright/test';
import base from './playwright.config';

export default defineConfig({ ...base, testDir: './review-tests', webServer: [
  ...(Array.isArray(base.webServer) ? base.webServer.slice(0, 1) : []),
  { command: 'npm run dev -- --config vite.review.config.ts', url: 'http://127.0.0.1:5173', reuseExistingServer: false, timeout: 120_000 },
] });

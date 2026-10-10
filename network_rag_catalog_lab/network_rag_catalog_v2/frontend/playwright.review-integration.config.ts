import { defineConfig } from '@playwright/test';
import base from './playwright.review.config';

export default defineConfig({ ...base, testDir: './review-integration', timeout: 90_000,
  webServer: Array.isArray(base.webServer) ? base.webServer.slice(1) : [],
});

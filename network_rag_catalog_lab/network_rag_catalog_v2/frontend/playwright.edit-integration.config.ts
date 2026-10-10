import { defineConfig } from '@playwright/test';
import base from './playwright.review-integration.config';
export default defineConfig({ ...base, testDir: './edit-integration' });

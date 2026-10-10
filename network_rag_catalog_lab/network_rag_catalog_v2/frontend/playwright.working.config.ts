import { defineConfig } from '@playwright/test';
import base from './playwright.originals.config';

export default defineConfig({ ...base, testDir: './working-integration' });

import { defineConfig, mergeConfig } from 'vite';
import base from './vite.config';

// Explicit test server only. Normal dev/build has no proposal producer/global.
export default defineConfig(async (environment) => mergeConfig(await (typeof base === 'function' ? base(environment) : base), {
  plugins: [{ name: 'review-test-entry', enforce: 'pre', transform(code: string, id: string) {
    if (!id.replaceAll('\\', '/').endsWith('/src/main.tsx')) return;
    return { code: `import { ReviewHarness } from '/review-harness/ReviewHarness.tsx';\n${code.replace('<App />', '<App /><ReviewHarness />')}`, map: null };
  } }],
}));

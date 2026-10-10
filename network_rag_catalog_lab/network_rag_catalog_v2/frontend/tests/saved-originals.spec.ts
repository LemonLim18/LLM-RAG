import { expect, test, type Page } from '@playwright/test';
import type { GeneratedOriginal } from '../src/services/originalsApi';
import type { PlanningResponse } from '../src/services/planningApi';

const endpoint = '**/api/v1/workbench/artifacts/generated-originals';
const id = '00000000-0000-4000-8000-000000000111';
const text = '! immutable Cisco original\r\nrouter ospf 10\r\n  ! spaces  \r\n';
function artifact(suffix = '1', device = 'R1'): GeneratedOriginal {
  return { schema_version: 1, kind: 'generated_original', artifact_id: 'original-' + suffix.repeat(64),
    source: { session_id: id, session_revision: 'a'.repeat(64), task_id: `task-${device}`, device_id: `dev-${device.toLowerCase()}`, config_index: 0 },
    logical_intent_id: 'intent-ospf', category: 'routing', operation_id: 'configure_ospf', hostname: device, vendor: 'cisco', platform: 'ios', version: '15',
    captured_at: '2026-10-09T00:00:00+00:00', content_sha256: 'c'.repeat(64), content_encoding: 'utf-8',
    authority: { plan_runtime_authority: 'direct_files' }, validity: 'historical_not_checked',
    configuration: device === 'R1' ? text : '! R2 separate\nrouter ospf 20\n', record_sha256: 'd'.repeat(64) };
}
function planning(): PlanningResponse {
  const device = { id: 'dev-r1', hostname: 'R1', vendor: 'cisco', platform: 'ios', version: '15' };
  return { api_version: 1, mode: 'local_v9', inventory_source: 'synthetic', client_request_id: '', session_revision: 'a'.repeat(64),
    session: { session_id: id, status: 'ready', pending_questions: [], plan: { original_prompt: 'Configure OSPF', status: 'ready',
      runtime_authority: 'direct_files', knowledge_snapshot_id: '', issues: [], tasks: [{ intent_id: 'task-R1', logical_intent_id: 'intent-ospf', device_id: 'dev-r1',
        operation_id: 'configure_ospf', status: 'rendered', feedback: '', parameters: {}, target_refs: ['R1'], target_devices: [device], issues: [],
        configs: [{ device_id: 'dev-r1', hostname: 'R1', vendor: 'cisco', platform: 'ios', configuration: text }] }] } } };
}
async function openPreview(page: Page) {
  // A passive historical restore keeps this suite focused on explicit original
  // capture. Fresh single-output generation now opens a working file by design.
  await page.route(`**/api/v1/planning/sessions/${id}`, (route) => route.fulfill({ json: { ...planning(), origin: 'saved_session', freshness: 'not_checked', mutation_eligibility: 'not_checked' } }));
  await page.goto('/');
  await page.locator('.view-lines').click(); await page.keyboard.press('Control+End'); await page.keyboard.insertText('\n! KEEP-SAMPLE');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Saved session ID', { exact: true }).fill(id);
  await page.getByRole('button', { name: 'Restore saved session', exact: true }).click();
  await page.getByRole('button', { name: 'Open read-only in Monaco · output 1', exact: true }).click();
}
async function editorState(page: Page) {
  return page.evaluate(async () => {
    const url = performance.getEntriesByType('resource').map((item) => item.name).find((name) => /\/@monaco-editor_react\.js\?/.test(name));
    if (!url) throw new Error('Missing application Monaco module');
    const { loader } = await import(/* @vite-ignore */ url);
    const api = await loader.init() as typeof import('monaco-editor');
    return { models: api.editor.getModels().map((model) => ({ uri: model.uri.toString(), text: model.getValue(undefined, true) })),
      editors: api.editor.getEditors().map((editor) => ({ uri: editor.getModel()?.uri.toString(), readOnly: editor.getOption(api.editor.EditorOption.readOnly), domReadOnly: editor.getOption(api.editor.EditorOption.domReadOnly) })) };
  });
}
async function assertOriginal(page: Page, item: GeneratedOriginal) {
  await expect(page.getByLabel('Saved original document').locator('.monaco-editor')).toBeVisible();
  await expect.poll(async () => (await editorState(page)).models.filter((model) => model.uri.startsWith('inmemory://v9-original/')))
    .toEqual([{ uri: `inmemory://v9-original/${item.artifact_id}/configuration`, text: item.configuration }]);
  expect((await editorState(page)).editors).toMatchObject([{ readOnly: true, domReadOnly: true }]);
  await expect(page.getByText('Historical captured output · current validity not checked · not deployed')).toBeVisible();
}
const row = (page: Page, device = 'R1') => page.getByRole('button', { name: new RegExp(`^Open saved original ${device} `) });

test('explicit capture, pending guard, Explorer discovery, real read-only Monaco and sample isolation', async ({ page, context }) => {
  const records: GeneratedOriginal[] = [];
  let posts = 0;
  let release!: () => void;
  const wait = new Promise<void>((resolve) => { release = resolve; });
  await page.route(endpoint, async (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ json: { api_version: 1, limit: 128, artifacts: records } });
    posts++;
    expect(route.request().postDataJSON()).toEqual({ session_id: id, expected_session_revision: 'a'.repeat(64), task_id: 'task-R1', device_id: 'dev-r1', config_index: 0 });
    await wait;
    if (!records.length) records.push(artifact());
    return route.fulfill({ status: posts === 1 ? 201 : 200, json: { api_version: 1, outcome: posts === 1 ? 'created' : 'already_saved', artifact: records[0] } });
  });
  await page.route(endpoint + '/*', (route) => route.fulfill({ json: records[0] }));
  await openPreview(page);
  const save = page.getByRole('button', { name: 'Save to Workspace', exact: true });
  await save.click(); await expect(save).toBeDisabled(); expect(posts).toBe(1); release();
  await expect(page.getByText('Saved original confirmed.', { exact: false })).toBeVisible();
  await save.click(); await expect(page.getByText('Already saved —', { exact: false })).toBeVisible();
  await expect(row(page)).toHaveCount(1); await row(page).click(); await assertOriginal(page, records[0]);
  await page.getByLabel('Saved original document').locator('.view-lines').click(); await page.keyboard.type('NOT-ALLOWED');
  await context.grantPermissions(['clipboard-read', 'clipboard-write']); await page.evaluate(() => navigator.clipboard.writeText('NO-PASTE')); await page.keyboard.press('Control+V');
  await assertOriginal(page, records[0]);
  await page.getByRole('tab', { name: 'Samples', exact: true }).click();
  await expect(page.locator('.view-lines')).toContainText('KEEP-SAMPLE');
  await expect.poll(async () => (await editorState(page)).models.filter((model) => model.uri.startsWith('inmemory://v9-original/')).length).toBe(0);
  expect((await editorState(page)).editors.every((editor) => !editor.readOnly)).toBe(true);
  await row(page).click(); await assertOriginal(page, records[0]);
  await page.reload(); await row(page).click(); await assertOriginal(page, records[0]); expect(posts).toBe(2);
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await page.getByRole('button', { name: 'Add Device', exact: true }).click(); await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Close registration', exact: true }).click();
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await page.getByLabel('Message the demo Copilot').fill('Original is independent'); await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Original is independent”')).toBeVisible();
});

test('lost capture response stays uncertain; passive refresh discovers saved result without POST replay', async ({ page }) => {
  const records: GeneratedOriginal[] = []; let posts = 0; const mutations: string[] = [];
  page.on('request', (request) => { if (request.method() !== 'GET' && request.url().includes('/api/')) mutations.push(request.url()); });
  await page.route(endpoint, (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ json: { api_version: 1, limit: 128, artifacts: records } });
    posts++; records.push(artifact()); return route.abort('connectionreset');
  });
  await page.route(endpoint + '/*', (route) => route.fulfill({ json: records[0] }));
  await openPreview(page); await page.getByRole('button', { name: 'Save to Workspace' }).click();
  await expect(page.getByLabel('Read-only V9 configuration', { exact: true }).getByRole('alert')).toContainText('OUTCOME_UNCERTAIN');
  await expect(row(page)).toHaveCount(0);
  await page.getByRole('button', { name: 'Refresh Saved Originals' }).click(); await row(page).click(); await assertOriginal(page, records[0]);
  await page.reload(); await row(page).click(); await assertOriginal(page, records[0]);
  expect(posts).toBe(1); expect(mutations).toHaveLength(1); // Passive restore, explicit capture only.
});

test('stale source, association and storage failures are explicit; list/detail failures do not break samples', async ({ page }) => {
  let code = 'STALE_SOURCE_SESSION'; let listingFailure = false;
  await page.route(endpoint, (route) => route.request().method() === 'POST'
    ? route.fulfill({ status: 409, json: { detail: { code, message: 'Original not confirmed.' } } })
    : listingFailure ? route.fulfill({ status: 503, json: { detail: { code: 'ARTIFACT_STORAGE_UNAVAILABLE', message: 'Storage unavailable.' } } })
    : route.fulfill({ json: { api_version: 1, limit: 128, artifacts: [artifact()] } }));
  await page.route(endpoint + '/*', (route) => route.fulfill({ status: 409, json: { detail: { code: 'CORRUPT_ARTIFACT', message: 'Integrity verification failed.' } } }));
  await openPreview(page);
  for (const failure of ['STALE_SOURCE_SESSION', 'SOURCE_ASSOCIATION_ERROR', 'ARTIFACT_STORAGE_UNAVAILABLE']) {
    code = failure; await page.getByRole('button', { name: 'Save to Workspace' }).click();
    await expect(page.getByLabel('Read-only V9 configuration', { exact: true }).getByRole('alert')).toContainText(failure);
  }
  await row(page).click(); await expect(page.getByLabel('Configuration workspace').getByRole('alert')).toContainText('CORRUPT_ARTIFACT');
  await expect(page.getByLabel('Read-only saved original editor')).toHaveCount(0);
  listingFailure = true; await page.getByRole('button', { name: 'Refresh Saved Originals' }).click();
  await expect(page.getByLabel('Saved Originals').getByRole('alert')).toContainText('ARTIFACT_STORAGE_UNAVAILABLE');
  await page.getByRole('tab', { name: 'Samples', exact: true }).click(); await expect(page.locator('.view-lines')).toContainText('KEEP-SAMPLE');
});

test('multiple originals have distinct models and task/device provenance; read navigation has no mutations', async ({ page }, testInfo) => {
  const records = [artifact(), artifact('2', 'R2')]; const mutations: string[] = [];
  page.on('request', (request) => { if (request.method() !== 'GET' && request.url().includes('/api/')) mutations.push(request.url()); });
  await page.route(endpoint, (route) => route.fulfill({ json: { api_version: 1, limit: 128, artifacts: records } }));
  await page.route(endpoint + '/*', (route) => route.fulfill({ json: records.find((item) => route.request().url().endsWith(item.artifact_id)) }));
  await page.goto('/');
  for (const item of records) {
    await row(page, item.hostname!).click(); await assertOriginal(page, item);
    await page.getByText('Original identity and captured provenance', { exact: true }).click();
    await expect(page.getByLabel('Saved original document')).toContainText(item.source.task_id);
    await expect(page.getByLabel('Saved original document')).toContainText(item.source.device_id);
    await page.getByText('Original identity and captured provenance', { exact: true }).click();
  }
  await page.screenshot({ path: testInfo.outputPath('saved-original-workbench.png') });
  expect(mutations).toEqual([]);
});

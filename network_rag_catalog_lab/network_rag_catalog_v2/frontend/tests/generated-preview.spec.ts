import { expect, test, type Page } from '@playwright/test';
import type { PlanningResponse, PlanningTask, SessionSnapshot } from '../src/services/planningApi';

const sessionId = '00000000-0000-4000-8000-000000000110';
const r1 = { id: 'dev-r1', hostname: 'R1', vendor: 'cisco', platform: 'iosxe', version: '17.9' };
const r2 = { id: 'dev-r2', hostname: 'R2', vendor: 'huawei', platform: 'vrp', version: '8' };
const cisco = '! exact preview\r\nrouter ospf 10\r\n network 10.0.0.0 0.0.0.255 area 0\r\n! repeated\r\n! repeated\r\n';
function config(device = r1, configuration = cisco) {
  return { device_id: device.id, hostname: device.hostname, vendor: device.vendor, platform: device.platform,
    version: device.version, parameters: {}, configuration };
}
function task(id: string, intent: string, device = r1, configuration = cisco): PlanningTask {
  return { intent_id: id, logical_intent_id: intent, device_id: device.id, operation_id: intent === 'intent-ospf' ? 'configure_ospf' : 'create_vlan',
    status: 'rendered', feedback: '', parameters: {}, target_refs: [device.hostname], target_devices: [device],
    issues: [], configs: [config(device, configuration)], revision: 1 };
}
function fixture(): PlanningResponse {
  return { api_version: 1, mode: 'local_v9', inventory_source: 'synthetic', client_request_id: 'set-by-route', session_revision: 'a'.repeat(64),
    session: { session_id: sessionId, status: 'ready', plan: { original_prompt: 'Review generated device configurations', status: 'ready',
      runtime_authority: 'files', knowledge_snapshot_id: '', issues: [], intents: [
        { intent_id: 'intent-ospf', request_text: 'Configure OSPF on R1 and R2', target_refs: ['R1', 'R2'], target_text: 'R1 and R2', source_spans: [], issues: [] },
        { intent_id: 'intent-vlan', request_text: 'Create VLAN on R1', target_refs: ['R1'], target_text: 'R1', source_spans: [], issues: [] },
      ], tasks: [task('intent-ospf:dev-r1', 'intent-ospf'), task('intent-ospf:dev-r2', 'intent-ospf', r2, 'ospf 10\n area 0.0.0.0\n'),
        task('intent-vlan:dev-r1', 'intent-vlan', r1, 'vlan 120\n name REVIEW\n')] }, pending_questions: [] } };
}
async function creation(page: Page, response = fixture()) {
  await page.route('**/api/v1/planning/sessions', (route) => route.fulfill({ json: { ...response, client_request_id: route.request().postDataJSON().client_request_id } }));
}
async function submit(page: Page) {
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Review generated device configurations');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByLabel('Local V9 plan review')).toBeVisible();
}
async function openOutput(page: Page, index = 1) {
  await page.getByRole('button', { name: `Open read-only in Monaco · output ${index}`, exact: true }).click();
  // Chrome's native EditContext input is zero-sized; the rendered Monaco surface
  // is the visible editor. Its live model/options are asserted separately below.
  await expect(page.getByLabel('Read-only V9 configuration', { exact: true }).locator('.monaco-editor')).toBeVisible();
  await expect(page.getByLabel('Read-only V9 configuration editor', { exact: true })).toBeAttached();
}
async function monacoState(page: Page) {
  // Inspect the same locally bundled Monaco instance, not a mocked Editor or DOM text facsimile.
  return page.evaluate(async () => {
    // Match Vite's versioned module URL already loaded by the application. A
    // second unversioned module URL can create an independent loader singleton.
    const modulePath = performance.getEntriesByType('resource').map((entry) => entry.name)
      .find((url) => /\/@monaco-editor_react\.js\?/.test(url));
    if (!modulePath) throw new Error('Application Monaco module was not loaded');
    const { loader } = await import(/* @vite-ignore */ modulePath);
    const api = await loader.init() as typeof import('monaco-editor');
    return { models: api.editor.getModels().map((model) => ({ uri: model.uri.toString(), content: model.getValue(undefined, true) })),
      editors: api.editor.getEditors().map((editor) => ({ uri: editor.getModel()?.uri.toString(),
        readOnly: editor.getOption(api.editor.EditorOption.readOnly), domReadOnly: editor.getOption(api.editor.EditorOption.domReadOnly) })) };
  });
}
async function preview(page: Page, content: string) {
  const surface = page.getByLabel('Read-only V9 configuration', { exact: true }).locator('.view-lines');
  await expect(surface).toContainText(content.split(/\r?\n/).find((line) => line.trim())!);
  await expect.poll(async () => (await monacoState(page)).models.filter((model) => model.uri.startsWith('inmemory://v9-preview/')).map((model) => model.content)).toEqual([content]);
  const snapshot = await monacoState(page);
  expect(snapshot.editors.filter((editor) => editor.uri?.startsWith('inmemory://v9-preview/'))).toMatchObject([{ readOnly: true, domReadOnly: true }]);
  return snapshot.models.find((model) => model.uri.startsWith('inmemory://v9-preview/'))!.uri;
}
async function noPreviewModel(page: Page) {
  await expect.poll(async () => (await monacoState(page)).models.filter((model) => model.uri.startsWith('inmemory://v9-preview/')).length).toBe(0);
}
function saved(result: SessionSnapshot) {
  return { ...result, origin: 'saved_session', freshness: 'not_checked', mutation_eligibility: 'not_checked' };
}

test('real Monaco enforces read-only output and isolates samples and task/device identities', async ({ page, context }) => {
  await creation(page);
  const mutations: string[] = [];
  page.on('request', (request) => { if (request.method() !== 'GET' && request.url().includes('/api/')) mutations.push(request.url()); });
  await page.goto('/');
  await page.locator('.view-lines').click(); await page.keyboard.press('Control+End'); await page.keyboard.insertText('\n! SAMPLE-UNCHANGED');
  const samples = (await monacoState(page)).models.filter((model) => model.uri.startsWith('inmemory://demo/'));
  expect(samples.length).toBeGreaterThan(0);
  expect(samples.some((model) => model.content.includes('SAMPLE-UNCHANGED'))).toBe(true);
  await submit(page); await openOutput(page);
  const firstPath = await preview(page, cisco);
  const viewer = page.getByLabel('Read-only V9 configuration', { exact: true });
  await expect(viewer).toContainText('R1 · cisco · iosxe');
  await viewer.getByText('Session, task and device provenance', { exact: true }).click();
  await expect(viewer).toContainText(sessionId); await expect(viewer).toContainText('intent-ospf:dev-r1');
  await expect(viewer).toContainText('intent-ospf'); await expect(viewer).toContainText('dev-r1');
  await viewer.locator('.view-lines').click(); await page.keyboard.press('Control+End'); await page.keyboard.type('SHOULD-NOT-APPEAR');
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.evaluate(() => navigator.clipboard.writeText('PASTE-MUST-NOT-CHANGE'));
  await page.keyboard.press('Control+V');
  await preview(page, cisco);
  await page.getByRole('tab', { name: 'Samples', exact: true }).click(); await noPreviewModel(page);
  expect((await monacoState(page)).models.filter((model) => model.uri.startsWith('inmemory://demo/'))).toEqual(samples);
  expect((await monacoState(page)).editors.every((editor) => !editor.readOnly)).toBe(true);
  await page.locator('.view-lines').click(); await page.keyboard.press('Control+End'); await page.keyboard.insertText('\n! STILL-EDITABLE');
  await page.getByRole('tab', { name: 'V9 preview', exact: true }).click(); expect(await preview(page, cisco)).toBe(firstPath);
  const paths = new Set([firstPath]);
  for (const [id, text] of [['intent-ospf:dev-r2', 'ospf 10\n area 0.0.0.0\n'], ['intent-vlan:dev-r1', 'vlan 120\n name REVIEW\n']]) {
    await page.getByRole('tab', { name: 'V9 plan review', exact: true }).click();
    await page.getByRole('option', { name: new RegExp(id) }).click(); await openOutput(page); paths.add(await preview(page, text));
  }
  expect(paths.size).toBe(3);
  expect(mutations).toHaveLength(1); // Only the explicit creation, no preview-triggered POST/save/answer.
  await page.getByRole('button', { name: 'Close preview', exact: true }).click(); await noPreviewModel(page);
  await expect(page.getByRole('tab', { name: 'V9 preview', exact: true })).toBeDisabled();
  await page.getByRole('tab', { name: 'Samples', exact: true }).click(); await expect(page.locator('.view-lines')).toContainText('STILL-EDITABLE');
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await page.getByLabel('Message the demo Copilot').fill('Separate preview'); await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Separate preview”')).toBeVisible(); expect(mutations).toHaveLength(1);
});

test('multiple config entries are distinct; missing or mismatched device output cannot open', async ({ page }) => {
  const response = fixture(); const first = response.session.plan.tasks[0];
  first.device_id = null; first.target_devices = [r1, r2];
  first.configs = [config(), config(r1, 'vlan 222\n'), config(r2, 'sysname R2\n')];
  const blocked = response.session.plan.tasks[1]; blocked.status = 'needs_clarification'; blocked.configs = [];
  const invalid = response.session.plan.tasks[2]; invalid.status = 'failed';
  invalid.configs = [config(r2, 'WRONG DEVICE'), { configuration: 'NO ID' }, config(r1, ''), { ...config(), configuration: null }];
  await creation(page, response); await page.goto('/'); await submit(page);
  const uris = new Set<string>();
  for (const [index, content] of [[1, cisco], [2, 'vlan 222\n'], [3, 'sysname R2\n']] as const) {
    await openOutput(page, index); uris.add(await preview(page, content));
    await page.getByRole('tab', { name: 'V9 plan review', exact: true }).click(); await noPreviewModel(page);
  }
  expect(uris.size).toBe(3);
  await page.getByRole('option', { name: /intent-ospf:dev-r2/ }).click();
  await expect(page.getByLabel('Task details intent-ospf:dev-r2')).toContainText('No generated configuration is present');
  await expect(page.getByRole('button', { name: /Open read-only in Monaco/ })).toHaveCount(0);
  await page.getByRole('option', { name: /intent-vlan:dev-r1/ }).click();
  await expect(page.getByLabel('Task details intent-vlan:dev-r1')).toContainText('Monaco preview unavailable');
  await expect(page.getByRole('button', { name: /Open read-only in Monaco/ })).toHaveCount(0);
});

test('confirmed clarification revision closes old preview; reopened Monaco uses only updated output', async ({ page }) => {
  const response = fixture();
  // Transport lifecycle stress fixture: retained output alongside a pending question.
  // This is not a claim that V9's current request-wide renderer produces that combination.
  response.session.status = 'needs_clarification';
  response.session.plan.status = 'needs_clarification';
  response.session.pending_questions = [{ question_id: 'q-area', task_id: 'intent-ospf:dev-r1', revision: 1, source_revision: 'source',
    wording: 'What area?', field_path: 'area', multiple: false, allow_custom: true, expected_schema: { type: 'string' }, options: [] }];
  let answers = 0;
  await page.route('**/answers', async (route) => {
    answers++; const request = route.request().postDataJSON();
    const updated = structuredClone(response); updated.session_revision = 'b'.repeat(64); updated.session.pending_questions = [];
    updated.session.status = 'ready'; updated.session.plan.status = 'ready'; updated.session.plan.tasks[0].configs = [config(r1, 'router ospf 20\n')];
    await route.fulfill({ json: { ...updated, client_request_id: request.client_request_id, accepted: true, answered_question_id: 'q-area' } });
  });
  await creation(page, response); await page.goto('/'); await submit(page); await openOutput(page); const oldPath = await preview(page, cisco);
  await page.getByLabel('Answer value', { exact: true }).fill('0'); await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect(page.getByLabel('Local V9 plan review')).toBeVisible();
  await expect(page.getByText('The previous V9 preview was closed', { exact: false })).toBeVisible();
  await noPreviewModel(page); await expect(page.getByRole('tab', { name: 'V9 preview', exact: true })).toBeDisabled();
  await openOutput(page); expect(await preview(page, 'router ospf 20\n')).not.toBe(oldPath); expect(answers).toBe(1);
});

test('pending clarification produces a newly viewable ready configuration at compact desktop size', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const response = fixture(); response.session.status = 'needs_clarification'; response.session.plan.status = 'needs_clarification';
  response.session.plan.tasks = [task('intent-ospf:dev-r1', 'intent-ospf')];
  response.session.plan.tasks[0].configs = []; response.session.plan.tasks[0].status = 'needs_clarification';
  response.session.pending_questions = [{ question_id: 'q-area', task_id: 'intent-ospf:dev-r1', revision: 1, source_revision: 'source',
    wording: 'What area?', field_path: 'area', multiple: false, allow_custom: true, expected_schema: { type: 'string' }, options: [] }];
  await page.route('**/answers', (route) => {
    const request = route.request().postDataJSON(); const updated = structuredClone(response);
    updated.session_revision = 'b'.repeat(64); updated.session.status = 'ready'; updated.session.plan.status = 'ready';
    updated.session.plan.tasks[0].status = 'rendered'; updated.session.plan.tasks[0].configs = [config()]; updated.session.pending_questions = [];
    return route.fulfill({ json: { ...updated, client_request_id: request.client_request_id, accepted: true, answered_question_id: 'q-area' } });
  });
  await creation(page, response); await page.goto('/'); await submit(page);
  await expect(page.getByRole('button', { name: /Open read-only in Monaco/ })).toHaveCount(0);
  await page.getByLabel('Answer value', { exact: true }).fill('0'); await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await openOutput(page); await preview(page, cisco);
  const box = await page.getByLabel('Read-only V9 configuration', { exact: true }).locator('.monaco-editor').boundingBox();
  expect(box?.width).toBeGreaterThan(300); expect(box?.height).toBeGreaterThan(150);
  await page.screenshot({ path: testInfo.outputPath('read-only-preview.png') });
});

test('withdrawal, config reordering and session replacement never retain an old preview', async ({ page }) => {
  const response = fixture(); let current = structuredClone(response);
  await creation(page, response);
  await page.route(`**/planning/sessions/${sessionId}`, (route) => route.fulfill({ json: saved(current) }));
  await page.goto('/'); await submit(page); await openOutput(page); await preview(page, cisco);
  current.session_revision = 'c'.repeat(64); current.session.plan.tasks[0].configs = [];
  current.session.plan.tasks[0].status = 'needs_clarification';
  await page.getByRole('button', { name: 'Read latest saved state' }).click(); await noPreviewModel(page);
  await expect(page.getByLabel('Task details intent-ospf:dev-r1')).toContainText('No generated configuration is present');
  await expect(page.getByRole('tab', { name: 'V9 preview', exact: true })).toBeDisabled();
  current = structuredClone(response); current.session_revision = 'd'.repeat(64);
  current.session.plan.tasks[0].configs = [config(r1, 'vlan 222\n'), config()];
  await page.getByRole('button', { name: 'Read latest saved state' }).click(); await openOutput(page, 2); await preview(page, cisco);
  current.session_revision = 'e'.repeat(64); current.session.plan.tasks[0].configs.reverse();
  await page.getByRole('button', { name: 'Read latest saved state' }).click(); await noPreviewModel(page);
  await openOutput(page, 2); await preview(page, 'vlan 222\n');
  const replacement = fixture(); replacement.session.session_id = '00000000-0000-4000-8000-000000000111';
  replacement.session.plan.tasks = [task('replacement', 'intent-vlan', r1, 'vlan 999\n')];
  await creation(page, replacement); await submit(page); await noPreviewModel(page);
  await expect(page.getByRole('tab', { name: 'V9 preview', exact: true })).toBeDisabled();
  await openOutput(page); await preview(page, 'vlan 999\n');
});

test('explicit restored historical preview uses saved provenance without mutation or auto-recovery', async ({ page }) => {
  const response = fixture(); let reads = 0; const mutations: string[] = [];
  page.on('request', (request) => { if (request.method() !== 'GET' && request.url().includes('/api/')) mutations.push(request.url()); });
  await page.route(`**/planning/sessions/${sessionId}`, (route) => { reads++; return route.fulfill({ json: saved(response) }); });
  await page.goto('/');
  await page.evaluate(({ sessionId, revision }) => localStorage.setItem('v9.session-recovery.v1', JSON.stringify({
    reference: { sessionId, revision, answerUncertain: false },
  })), { sessionId, revision: response.session_revision });
  await page.reload(); await page.getByRole('button', { name: 'Local V9', exact: true }).click(); expect(reads).toBe(0);
  await page.getByLabel('Saved session ID', { exact: true }).fill(sessionId);
  await page.getByRole('button', { name: 'Restore saved session', exact: true }).click();
  await openOutput(page); await preview(page, cisco);
  await expect(page.getByLabel('Read-only V9 configuration', { exact: true })).toContainText('Saved historical state · current validity not checked');
  await page.getByRole('tab', { name: 'Samples', exact: true }).click();
  await page.getByRole('tab', { name: 'V9 preview', exact: true }).click(); await preview(page, cisco);
  expect(reads).toBe(1); expect(mutations).toEqual([]);
});

test('inventory revision change labels the retained Monaco preview historical without changing its content', async ({ page }) => {
  await creation(page); let inventoryRevision = 'a'.repeat(64); let mutations = 0;
  await page.route('**/inventory/devices', async (route) => {
    if (route.request().method() !== 'GET') { mutations++; return route.abort(); }
    const body = await (await route.fetch()).json(); body.inventory_revision = inventoryRevision; return route.fulfill({ json: body });
  });
  await page.goto('/'); await submit(page); await openOutput(page); const path = await preview(page, cisco);
  await page.getByRole('button', { name: 'Add Device', exact: true }).click(); inventoryRevision = 'f'.repeat(64);
  await page.getByRole('button', { name: 'Reload inventory revision', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Inventory reloaded');
  await page.getByRole('button', { name: 'Close registration' }).click();
  expect(await preview(page, cisco)).toBe(path);
  await expect(page.getByLabel('Read-only V9 configuration', { exact: true })).toContainText('Saved historical state · current validity not checked');
  expect(mutations).toBe(0);
});

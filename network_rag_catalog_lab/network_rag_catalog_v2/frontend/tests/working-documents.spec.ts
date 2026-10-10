import { expect, test, type Page } from '@playwright/test';
import type { GeneratedOriginal } from '../src/services/originalsApi';
import type { WorkingDocument } from '../src/services/workingApi';
import type { PlanningResponse } from '../src/services/planningApi';

const sessionId = '00000000-0000-4000-8000-000000000112';
const base = '**/api/v1/workbench/working-documents';
const originalsUrl = '**/api/v1/workbench/artifacts/generated-originals';
const initial = 'vlan 100\n name SALES\n';
function original(n = 1): GeneratedOriginal {
  return { schema_version: 1, kind: 'generated_original', artifact_id: 'original-' + String(n).repeat(64),
    source: { session_id: sessionId, session_revision: 'a'.repeat(64), task_id: `task-r${n}`, device_id: `dev-r${n}`, config_index: 0 },
    logical_intent_id: 'logical-vlan', category: 'switching', operation_id: 'create_vlan', hostname: `R${n}`, vendor: 'cisco', platform: 'ios', version: '15',
    captured_at: '2026-10-09T00:00:00Z', content_sha256: 'c'.repeat(64), content_encoding: 'utf-8', authority: { plan_runtime_authority: 'direct_files' },
    validity: 'historical_not_checked', configuration: initial, record_sha256: 'd'.repeat(64) };
}
function document(n = 1): WorkingDocument {
  return { schema_version: 1, document_id: 'working-' + String(n).repeat(64), original: original(n), revision: `00000000-0000-4000-8000-00000000000${n}`,
    save_sequence: 0, created_at: '2026-10-09T00:00:00Z', updated_at: '2026-10-09T00:00:00Z', content_sha256: 'e'.repeat(64),
    encoding: 'utf-8', validation: 'unvalidated', deployment: 'not_deployed', content: initial, record_sha256: 'f'.repeat(64) };
}
function plan(count = 1): PlanningResponse {
  return { api_version: 1, mode: 'local_v9', inventory_source: 'synthetic', client_request_id: '', session_revision: 'a'.repeat(64),
    session: { session_id: sessionId, status: 'ready', pending_questions: [], plan: { original_prompt: 'Create VLAN 100', status: 'ready',
      runtime_authority: 'direct_files', issues: [], tasks: Array.from({ length: count }, (_, i) => ({ intent_id: `task-r${i + 1}`, logical_intent_id: 'logical-vlan',
        device_id: `dev-r${i + 1}`, operation_id: 'create_vlan', status: 'rendered', feedback: '', parameters: { vlan_id: 100 }, target_refs: [`R${i + 1}`],
        target_devices: [{ id: `dev-r${i + 1}`, hostname: `R${i + 1}`, vendor: 'cisco', platform: 'ios' }], issues: [],
        configs: [{ device_id: `dev-r${i + 1}`, hostname: `R${i + 1}`, vendor: 'cisco', platform: 'ios', configuration: initial }] })) } } };
}
async function fixture(page: Page, count = 1) {
  const records: Record<string, WorkingDocument> = {};
  const captured: GeneratedOriginal[] = [];
  const mutations: string[] = [];
  page.on('request', (r) => { if (r.method() !== 'GET' && r.url().includes('/api/')) mutations.push(r.method() + ' ' + r.url()); });
  await page.route('**/api/v1/planning/sessions', (route) => route.fulfill({ json: { ...plan(count), client_request_id: route.request().postDataJSON().client_request_id } }));
  await page.route(`**/api/v1/planning/sessions/${sessionId}`, (route) => route.fulfill({ json: { ...plan(count), origin: 'saved_session', freshness: 'not_checked', mutation_eligibility: 'not_checked' } }));
  await page.route(originalsUrl, (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ json: { api_version: 1, artifacts: captured, limit: 128 } });
    const source = route.request().postDataJSON(); expect(source).not.toHaveProperty('configuration');
    const item = original(Number(source.device_id.slice(-1))); expect(source.task_id).toBe(item.source.task_id);
    if (!captured.some((x) => x.artifact_id === item.artifact_id)) captured.push(item);
    return route.fulfill({ status: 201, json: { api_version: 1, artifact: item, outcome: 'created' } });
  });
  await page.route(originalsUrl + '/*', (route) => route.fulfill({ json: captured.find((x) => route.request().url().endsWith(x.artifact_id)) }));
  await page.route(base, (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ json: { api_version: 1, documents: Object.values(records), limit: 128 } });
    const n = Number(route.request().postDataJSON().original_id.slice(-1)); const item = document(n);
    records[item.document_id] ??= item;
    return route.fulfill({ json: { api_version: 1, document: records[item.document_id], outcome: 'created' } });
  });
  await page.route(base + '/*', (route) => {
    const id = route.request().url().split('/').at(-1)!; const item = records[id];
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON(); expect(body.expected_revision).toBe(item.revision);
      records[id] = { ...item, content: body.content, revision: crypto.randomUUID(), save_sequence: item.save_sequence + 1 };
    }
    return route.fulfill({ json: records[id] });
  });
  return { records, captured, mutations };
}
async function submit(page: Page) {
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Create VLAN 100 on R1');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
}
async function state(page: Page) {
  return page.evaluate(async () => {
    const url = performance.getEntriesByType('resource').map((x) => x.name).find((x) => /\/@monaco-editor_react\.js\?/.test(x));
    const { loader } = await import(/* @vite-ignore */ url!);
    const api = await loader.init() as typeof import('monaco-editor');
    return api.editor.getEditors().map((editor) => ({ uri: editor.getModel()?.uri.toString(), text: editor.getModel()?.getValue(undefined, true), readOnly: editor.getOption(api.editor.EditorOption.readOnly) }));
  });
}
async function edit(page: Page, text: string) {
  await page.getByLabel('Editable working document').locator('.view-lines').click();
  await page.keyboard.press('Control+A'); await page.keyboard.insertText(text);
  await expect.poll(async () => (await state(page))[0]?.text).toBe(text);
}
const row = (page: Page, n = 1) => page.getByRole('button', { name: new RegExp(`^Open working file R${n} `) });

test('single confirmed output opens natively, Ctrl+S saves, Explorer reload reopens; original and sample stay independent', async ({ page }, info) => {
  const f = await fixture(page); await page.goto('/');
  await page.locator('.view-lines').click(); await page.keyboard.press('Control+End'); await page.keyboard.insertText('\n! SAMPLE-KEEP');
  await submit(page); await expect(page.getByLabel('Editable working document').locator('.monaco-editor')).toBeVisible();
  expect((await state(page))[0]).toMatchObject({ text: initial, readOnly: false });
  await edit(page, 'vlan 100\n name ENGINEERING\n');
  await expect(page.getByRole('tab', { name: /R1 · create_vlan/ })).toContainText('●');
  await page.keyboard.press('Control+s');
  await expect(page.getByText('Saved working content · UNVALIDATED · not deployed')).toBeVisible();
  expect(Object.values(f.records)[0].content).toContain('ENGINEERING'); expect(f.captured[0].configuration).toBe(initial);
  await page.getByRole('tab', { name: 'Samples', exact: true }).click(); await expect(page.locator('.view-lines')).toContainText('SAMPLE-KEEP');
  await page.getByRole('button', { name: /^Open saved original R1 / }).click(); await expect(page.getByLabel('Saved original document').locator('.monaco-editor')).toBeVisible(); expect((await state(page))[0].readOnly).toBe(true);
  await row(page).click(); await expect(page.locator('.view-lines')).toContainText('ENGINEERING');
  await page.reload(); await row(page).click(); await expect(page.locator('.view-lines')).toContainText('ENGINEERING');
  expect(f.mutations.filter((x) => x.includes('planning/sessions'))).toHaveLength(1);
  expect(f.mutations.filter((x) => x.startsWith('PUT'))).toHaveLength(1);
  expect(f.mutations).toHaveLength(4);
  await page.screenshot({ path: info.outputPath('native-working-editor.png') });
});

test('multiple device output links share normal opener, separate dirty tabs retain edits and revisiting never resets', async ({ page }) => {
  const f = await fixture(page, 2); await page.goto('/'); await submit(page);
  await expect(page.getByLabel('Local V9 plan review')).toBeVisible(); expect(f.captured).toHaveLength(0);
  await page.getByLabel('Local V9 session result').getByRole('button', { name: 'Open in Editor · dev-r1 · output 1', exact: true }).click();
  await edit(page, '! unsaved first');
  await page.getByLabel('Local V9 session result').getByRole('button', { name: 'Open in Editor · dev-r2 · output 1', exact: true }).click();
  await expect(page.getByLabel('Editable working document').locator('.view-lines')).toContainText('SALES'); await edit(page, '! unsaved second');
  await page.getByRole('tab', { name: /R1 · create_vlan/ }).click(); await expect(page.locator('.view-lines')).toContainText('unsaved first');
  await page.getByLabel('Local V9 session result').getByRole('button', { name: 'Open in Editor · dev-r1 · output 1', exact: true }).click();
  await expect(page.locator('.view-lines')).toContainText('unsaved first'); expect(Object.keys(f.records)).toHaveLength(2);
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click(); await page.getByLabel('Message the demo Copilot').fill('working independent');
  await page.getByRole('button', { name: 'Send demo message' }).click(); await expect(page.getByText('Mock response: I received “working independent”')).toBeVisible();
  await page.getByRole('button', { name: 'Add Device', exact: true }).click(); await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Close registration', exact: true }).click();
  await expect(page.locator('.view-lines')).toContainText('unsaved first');
});

test('pending save guards Ctrl+S and late response retains subsequent edits', async ({ page }) => {
  const f = await fixture(page); await page.goto('/'); await submit(page);
  await edit(page, '! first'); let release!: () => void; const wait = new Promise<void>((resolve) => { release = resolve; });
  await page.route(base + '/*', async (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    const item = Object.values(f.records)[0]; const body = route.request().postDataJSON();
    await wait; f.records[item.document_id] = { ...item, content: body.content, revision: crypto.randomUUID() };
    return route.fulfill({ json: f.records[item.document_id] });
  });
  await page.keyboard.press('Control+s'); await expect(page.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  await page.keyboard.press('Control+s'); await edit(page, '! later'); release();
  await expect(page.getByRole('button', { name: 'Save (Ctrl+S)', exact: true })).toBeEnabled();
  await expect(page.locator('.view-lines')).toContainText('later'); await expect(page.getByText('Unsaved changes · UNVALIDATED · not deployed')).toBeVisible();
  expect(f.mutations.filter((x) => x.startsWith('PUT'))).toHaveLength(1); expect(Object.values(f.records)[0].content).toBe('! first');
});

test('stale and lost save retain text; passive inspection and explicit reconciliation never replay writes', async ({ page }) => {
  const f = await fixture(page); await page.goto('/'); await submit(page); await edit(page, '! local');
  let lost = false;
  await page.route(base + '/*', (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    if (lost) { const item = Object.values(f.records)[0]; f.records[item.document_id] = { ...item, content: route.request().postDataJSON().content, revision: crypto.randomUUID() }; return route.abort('connectionreset'); }
    return route.fulfill({ status: 409, json: { detail: { code: 'STALE_WORKING_REVISION', message: 'Inspect latest saved state.' } } });
  });
  await page.keyboard.press('Control+s'); await expect(page.getByLabel('Editable working document').getByRole('alert')).toContainText('STALE_WORKING_REVISION');
  await expect(page.locator('.view-lines')).toContainText('local'); await expect(page.getByRole('button', { name: 'Save (Ctrl+S)' })).toBeDisabled();
  await page.getByRole('button', { name: 'Inspect saved state' }).click(); await page.getByRole('button', { name: 'Use latest revision, keep my text' }).click();
  lost = true; await page.getByRole('button', { name: 'Save (Ctrl+S)' }).click(); await expect(page.getByLabel('Editable working document').getByRole('alert')).toContainText('OUTCOME_UNCERTAIN');
  await page.getByRole('button', { name: 'Inspect saved state' }).click(); await expect(page.getByText(/Saved text matches local text/)).toBeVisible();
  expect(f.mutations.filter((x) => x.startsWith('PUT'))).toHaveLength(2);
  await page.getByRole('button', { name: 'Use latest revision, keep my text' }).click(); await expect(page.getByText('Saved working content · UNVALIDATED · not deployed')).toBeVisible();
});

test('historical restoration stays passive; partial capture failure and uncertain open use passive discovery', async ({ page }) => {
  const f = await fixture(page); let fail = true;
  await page.route(base, (route) => {
    if (route.request().method() === 'GET') return route.fallback();
    if (fail) return route.fulfill({ status: 503, json: { detail: { code: 'WORKING_STORAGE_UNAVAILABLE', message: 'Original retained; working storage unavailable.' } } });
    const item = document(); f.records[item.document_id] = item; return route.abort('connectionreset');
  });
  await page.goto('/'); await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Saved session ID', { exact: true }).fill(sessionId); await page.getByRole('button', { name: 'Restore saved session', exact: true }).click();
  await expect(page.getByLabel('Local V9 plan review')).toBeVisible(); expect(f.mutations).toEqual([]);
  await page.getByRole('button', { name: 'Open read-only in Monaco · output 1', exact: true }).click();
  await page.getByRole('button', { name: 'Open for Editing · dev-r1 · output 1' }).click();
  await expect(page.getByLabel('Working Files').getByRole('status')).toContainText('Original available; working file not confirmed'); expect(f.captured).toHaveLength(1);
  await page.getByRole('button', { name: /^Open saved original R1 / }).click(); fail = false;
  await page.getByRole('button', { name: 'Open for Editing', exact: true }).click();
  await expect(page.getByLabel('Working Files').getByRole('status')).toContainText('OUTCOME_UNCERTAIN');
  await page.getByRole('button', { name: 'Refresh Working Files' }).click(); await row(page).click();
  await expect(page.getByLabel('Editable working document')).toContainText('Historical source');
  expect(f.mutations).toHaveLength(3); expect(f.mutations.some((x) => x.includes('planning/sessions'))).toBe(false);
});

test('only a confirmed clarification completion opens the newly available working file', async ({ page }) => {
  const f = await fixture(page);
  const pending = plan(); pending.session.status = 'needs_clarification'; pending.session.plan.status = 'needs_clarification';
  pending.session.plan.tasks[0].configs = []; pending.session.plan.tasks[0].status = 'needs_clarification';
  pending.session.pending_questions = [{ question_id: 'q-name', task_id: 'task-r1', revision: 1, source_revision: 'source-1',
    wording: 'What VLAN name?', field_path: 'name', multiple: false, allow_custom: true, expected_schema: { type: 'string' }, options: [] }];
  await page.route('**/api/v1/planning/sessions', (route) => route.fulfill({ json: { ...pending, client_request_id: route.request().postDataJSON().client_request_id } }));
  let release!: () => void; const wait = new Promise<void>((resolve) => { release = resolve; });
  await page.route('**/answers', async (route) => {
    expect(route.request().postDataJSON().answer).toMatchObject({ question_id: 'q-name', kind: 'custom', raw_input: 'SALES' });
    await wait; const confirmed = plan(); confirmed.session_revision = 'b'.repeat(64);
    await route.fulfill({ json: { ...confirmed, client_request_id: route.request().postDataJSON().client_request_id, accepted: true, answered_question_id: 'q-name' } });
  });
  await page.route(originalsUrl, (route) => {
    if (route.request().method() === 'GET') return route.fallback();
    expect(route.request().postDataJSON().expected_session_revision).toBe('b'.repeat(64));
    const item = original(); item.source.session_revision = 'b'.repeat(64); f.captured.push(item);
    f.records[document().document_id] = { ...document(), original: item };
    return route.fulfill({ json: { api_version: 1, artifact: item, outcome: 'created' } });
  });
  await page.goto('/'); await submit(page); await expect(page.getByRole('form', { name: 'Answer current V9 question' })).toBeVisible();
  expect(f.captured).toHaveLength(0); await page.getByLabel('Answer value').fill('SALES');
  await page.getByRole('button', { name: 'Submit answer to V9' }).click(); expect(f.captured).toHaveLength(0); release();
  await expect(page.getByLabel('Editable working document').locator('.view-lines')).toContainText('SALES');
  expect(f.captured).toHaveLength(1); expect(Object.values(f.records)[0].original.source.session_revision).toBe('b'.repeat(64));
});

test('a late open does not steal navigation or overwrite the independently edited sample', async ({ page }) => {
  await fixture(page); let release!: () => void; const wait = new Promise<void>((resolve) => { release = resolve; });
  await page.route(base, async (route) => {
    if (route.request().method() === 'GET') return route.fallback();
    await wait; return route.fallback();
  });
  await page.goto('/'); await submit(page); await expect(page.getByLabel('Working Files').getByRole('status')).toContainText('Preparing');
  await page.getByRole('tab', { name: 'Samples', exact: true }).click();
  await page.locator('.view-lines').click(); await page.keyboard.press('Control+End'); await page.keyboard.insertText('\n! STILL-SAMPLE');
  release(); await expect(row(page)).toBeVisible(); await expect(page.getByRole('tab', { name: 'Samples', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('.view-lines')).toContainText('STILL-SAMPLE');
  await row(page).click(); await expect(page.getByLabel('Editable working document').locator('.view-lines')).toContainText('SALES');
});

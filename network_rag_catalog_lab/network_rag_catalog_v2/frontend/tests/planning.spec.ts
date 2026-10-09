import { expect, test } from '@playwright/test';

const fixture = {
  api_version: 1, mode: 'local_v9', inventory_source: 'synthetic', client_request_id: 'from-request', session_revision: 'saved-hash',
  session: {
    session_id: 'server-session-42', status: 'needs_clarification',
    plan: {
      original_prompt: 'Create a VLAN on R1 and R2', status: 'needs_clarification', runtime_authority: 'files', knowledge_snapshot_id: '', issues: [],
      tasks: ['dev-r1', 'dev-r2'].map((device, index) => ({
        intent_id: `intent-1:${device}`, operation_id: 'create_vlan', device_id: device, status: 'needs_clarification',
        parameters: { vlan_id: 100 }, target_refs: [`R${index + 1}`], feedback: '',
        target_devices: [{ id: device, hostname: `R${index + 1}`, vendor: index ? 'huawei' : 'cisco', platform: index ? 'vrp' : 'iosxe' }],
        issues: [{ type: 'MISSING', field: 'vlan_name' }], configs: [], parameter_evidence: { vlan_id: { source: 'user' } },
      })),
    },
    pending_questions: [{ question_id: 'question-from-v9', task_id: 'intent-1:dev-r1', wording: 'Which VLAN name?',
      revision: 3, source_revision: 'source-hash', field_path: 'name', multiple: false, allow_custom: true,
      expected_schema: { type: 'string' }, options: [{ option_id: 'stable-option', value: 'STAFF', label: 'STAFF' }] }],
  },
};

test('Local V9 pending, structured multi-target clarification and mock separation', async ({ page }) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let calls = 0;
  await page.route('**/api/v1/planning/sessions', async (route) => {
    calls++;
    const request = route.request().postDataJSON();
    expect(request.mode).toBe('local_v9');
    expect(request.client_request_id).toMatch(/^[0-9a-f-]{36}$/);
    await gate;
    await route.fulfill({ json: { ...fixture, client_request_id: request.client_request_id } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Create a VLAN on R1 and R2');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByText('V9 is processing…', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create Local V9 session' })).toBeDisabled();
  await expect(page.getByLabel('Request a Local V9 plan')).toBeDisabled();
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await page.getByRole('tab', { name: /r2-huawei.cfg/i }).click();
  await expect(page.locator('.view-lines')).toContainText('sysname R2');
  await page.getByRole('button', { name: 'Toggle AI Copilot' }).click();
  await page.getByRole('button', { name: 'Toggle AI Copilot' }).click();
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await expect(page.getByLabel('Request a Local V9 plan')).toBeDisabled();
  release();
  const result = page.getByRole('region', { name: 'Local V9 session result' });
  await expect(result).toContainText('server-session-42');
  await expect(result).toContainText('2 task(s)');
  await expect(result).toContainText('Which VLAN name?');
  await expect(result).toContainText('question-from-v9');
  await expect(result).toContainText('Only the current question can be answered');
  const review = page.getByLabel('Local V9 plan review');
  await expect(review).toContainText('intent-1:dev-r1');
  await expect(review).toContainText('intent-1:dev-r2');
  await page.getByRole('option', { name: /intent-1:dev-r2/ }).click();
  await expect(page.getByLabel('Task details intent-1:dev-r2')).toContainText('R2');
  await expect(page.getByLabel('Task details intent-1:dev-r2')).toContainText('100');
  expect(calls).toBe(1);
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await expect(result).toHaveCount(0);
  await page.getByLabel('Message the demo Copilot').fill('Mock only');
  await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Mock only”')).toBeVisible();
  expect(calls).toBe(1);
});

test('Local V9 errors never become demo results and lookup retains request identity', async ({ page }) => {
  const ids: string[] = [];
  await page.route('**/api/v1/planning/sessions', async (route) => {
    ids.push(route.request().postDataJSON().client_request_id);
    await route.fulfill({ status: 503, json: { detail: { code: 'LOCAL_SERVICE_UNAVAILABLE', message: 'Local model unavailable.' } } });
  });
  await page.route('**/api/v1/planning/requests/*', (route) => route.fulfill({ json: {
    api_version: 1, client_request_id: ids[0], status: 'unknown', message: 'No durable record is known.',
    session_id: null, session_revision: null, error_code: null,
  } }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Create VLAN 100 on R1');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByRole('complementary', { name: 'AI Copilot' }).getByRole('alert')).toContainText('LOCAL_SERVICE_UNAVAILABLE');
  await expect(page.getByRole('region', { name: 'Local V9 session result' })).toHaveCount(0);
  await expect(page.getByText(/Mock response:/)).toHaveCount(0);
  await page.getByRole('button', { name: 'Check creation outcome' }).click();
  await expect(page.getByRole('complementary', { name: 'AI Copilot' }).getByRole('alert')).toContainText('LOCAL_SERVICE_UNAVAILABLE');
  await expect(page.getByLabel('Saved session recovery')).toContainText('Creation outcome: unknown');
  expect(ids).toHaveLength(1);
  await page.getByRole('tab', { name: /r3-juniper.cfg/i }).click();
  await expect(page.locator('.view-lines')).toContainText('host-name R3');
  await page.getByRole('listitem', { name: /R2 Huawei/i }).click();
  await expect(page.locator('.view-lines')).toContainText('sysname R2');
});

test('transport failure presents unknown outcome rather than claiming cancellation', async ({ page }) => {
  await page.route('**/api/v1/planning/sessions', (route) => route.abort('connectionfailed'));
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Create VLAN 100 on R1');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByRole('complementary', { name: 'AI Copilot' }).getByRole('alert')).toContainText('outcome is unknown');
  await expect(page.getByRole('complementary', { name: 'AI Copilot' }).getByRole('alert')).toContainText('V9 may still save a session');
  await expect(page.locator('.monaco-editor')).toBeVisible();
});

test('opt-in real browser to FastAPI to V9 planning smoke', async ({ page }) => {
  test.skip(process.env.RUN_LIVE_V9 !== '1', 'Explicit local AI smoke only; creates a real saved session.');
  test.setTimeout(180_000);
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Create VLAN 100 named STAFF on R1');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  const result = page.getByRole('region', { name: 'Local V9 session result' });
  await expect(result).toContainText('Session: ready', { timeout: 125_000 });
  const review = page.getByLabel('Local V9 plan review');
  await expect(review).toContainText('create_vlan');
  await expect(review).toContainText('dev-r1');
  await expect(review).toContainText('vlan 100');
  console.log('REAL_BROWSER_SESSION', await result.locator('.planning-id').first().innerText());
});

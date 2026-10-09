import { expect, test, type Page } from '@playwright/test';
import type { PlanningResponse, ClarificationQuestion } from '../src/services/planningApi';

const question: ClarificationQuestion = {
  question_id: 'q-interface', task_id: 'intent-1', revision: 1, source_revision: 'source-1',
  wording: 'Which interface should this entry use?', field_path: 'interfaces', multiple: true, allow_custom: true,
  expected_schema: { type: 'array' }, options: [
    { option_id: 'stable-ge0', value: [{ name: 'ge-0/0/0' }], label: 'ge-0/0/0 (uplink)', explanation: 'Recorded interface on this device.' },
    { option_id: 'stable-ge1', value: [{ name: 'ge-0/0/1' }], label: 'ge-0/0/1 (edge)' },
  ],
};
const fixture: PlanningResponse = {
  api_version: 1, mode: 'local_v9', inventory_source: 'synthetic', client_request_id: 'creation-id', session_revision: 'a'.repeat(64),
  session: { session_id: '00000000-0000-4000-8000-000000000001', status: 'needs_clarification',
    plan: { original_prompt: 'Configure OSPF on R3', status: 'needs_clarification', runtime_authority: 'files', knowledge_snapshot_id: '', issues: [],
      tasks: [{ intent_id: 'intent-1', operation_id: 'configure_ospf', device_id: 'dev-r3', status: 'needs_clarification', feedback: '',
        parameters: {}, target_refs: ['R3'], target_devices: [{ id: 'dev-r3', hostname: 'R3', vendor: 'juniper', platform: 'junos' }], issues: [], configs: [] }] },
    pending_questions: [question],
  },
};
const areaQuestion: ClarificationQuestion = { ...question, question_id: 'q-area', revision: 2, field_path: 'interfaces[0].area',
  wording: 'ge-0/0/0: What area?', multiple: false, options: [], expected_schema: { type: 'string' } };

async function openFixture(page: Page, response = fixture) {
  await page.route('**/api/v1/planning/sessions', (route) => route.fulfill({ json: response }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Configure OSPF on R3');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByRole('form', { name: 'Answer current V9 question' })).toBeVisible();
}

test('stable option submission keeps confirmed state pending, then shows next question', async ({ page }) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let calls = 0;
  await page.route('**/answers', async (route) => {
    calls++;
    const request = route.request().postDataJSON();
    expect(request.expected_session_revision).toBe(fixture.session_revision);
    expect(request.answer).toMatchObject({ question_id: 'q-interface', revision: 1, source_revision: 'source-1', kind: 'selection', selected_ids: ['stable-ge0'], raw_input: '' });
    await gate;
    const updated = structuredClone(fixture);
    updated.session_revision = 'b'.repeat(64);
    updated.session.pending_questions = [areaQuestion];
    updated.session.plan.tasks[0].parameters = { interfaces: [{ name: 'ge-0/0/0' }] };
    await route.fulfill({ json: { ...updated, client_request_id: request.client_request_id, accepted: true, answered_question_id: 'q-interface' } });
  });
  await openFixture(page);
  const form = page.getByRole('form');
  await expect(form).toContainText('Recorded interface on this device.');
  await form.getByRole('checkbox', { name: /ge-0\/0\/0/ }).check();
  await form.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect(form.getByRole('button')).toBeDisabled();
  await expect(page.getByText('Submitting answer to V9…', { exact: false })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Local V9 session result' })).toContainText('q-interface');
  await page.getByRole('tab', { name: 'Samples' }).click();
  await page.getByRole('tab', { name: /r2-huawei.cfg/ }).click();
  await expect(page.locator('.view-lines')).toContainText('sysname R2');
  release();
  await expect(form).toContainText('ge-0/0/0: What area?');
  await expect(page.getByText('Answer accepted by V9.', { exact: false })).toBeVisible();
  expect(calls).toBe(1);
});

test('literal numeric custom answer reaches ready without selecting list position', async ({ page }) => {
  const start = structuredClone(fixture);
  start.session.pending_questions = [areaQuestion];
  await page.route('**/answers', async (route) => {
    const request = route.request().postDataJSON();
    expect(request.answer).toMatchObject({ question_id: 'q-area', kind: 'custom', raw_input: '1', selected_ids: [] });
    const updated = structuredClone(start);
    updated.session_revision = 'c'.repeat(64);
    updated.session.status = 'ready';
    updated.session.pending_questions = [];
    updated.session.plan.tasks[0].parameters = { interfaces: [{ name: 'ge-0/0/0', area: '1' }] };
    updated.session.plan.tasks[0].configs = [{ configuration: 'set protocols ospf area 1 interface ge-0/0/0' }];
    await route.fulfill({ json: { ...updated, client_request_id: request.client_request_id, accepted: true, answered_question_id: 'q-area' } });
  });
  await openFixture(page, start);
  await page.getByLabel('Answer value').fill('1');
  await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect(page.getByRole('region', { name: 'Local V9 session result' })).toContainText('Session: ready');
  await expect(page.getByRole('form')).toHaveCount(0);
  await expect(page.getByLabel('Local V9 plan review')).toContainText('set protocols ospf area 1');
});

test('stale answers keep confirmed session and block new mutation', async ({ page }) => {
  await page.route('**/answers', (route) => route.fulfill({ status: 409, json: { detail: { code: 'STALE_SESSION', message: 'Saved session changed; no answer applied.' } } }));
  await openFixture(page);
  await page.getByRole('form').getByRole('checkbox').first().check();
  await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect(page.getByRole('complementary', { name: 'AI Copilot' }).getByRole('alert')).toContainText('STALE_SESSION');
  await expect(page.getByRole('button', { name: 'Submit answer to V9' })).toBeDisabled();
  await expect(page.getByRole('region', { name: 'Local V9 session result' })).toContainText(fixture.session.session_id);
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await page.getByLabel('Message the demo Copilot').fill('Still separate');
  await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Still separate”')).toBeVisible();
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
});

test('lost response retries the exact answer ID and payload', async ({ page }) => {
  const requests: unknown[] = [];
  await page.route('**/answers', (route) => {
    requests.push(route.request().postDataJSON());
    return route.abort('connectionfailed');
  });
  await openFixture(page);
  await page.getByRole('form').getByRole('checkbox').first().check();
  await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect(page.getByRole('complementary', { name: 'AI Copilot' }).getByRole('alert')).toContainText('OUTCOME_UNKNOWN');
  await page.getByRole('button', { name: 'Retry same answer request' }).click();
  await expect.poll(() => requests.length).toBe(2);
  expect(requests[0]).toEqual(requests[1]);
  await expect(page.getByRole('button', { name: 'Submit answer to V9' })).toBeDisabled();
});

test('V9 validation rejection uses returned revision when user edits answer', async ({ page }) => {
  const start = structuredClone(fixture);
  start.session.pending_questions = [areaQuestion];
  let calls = 0;
  await page.route('**/answers', async (route) => {
    const request = route.request().postDataJSON();
    calls++;
    if (calls === 2) expect(request.expected_session_revision).toBe('d'.repeat(64));
    await route.fulfill({ status: 422, json: { detail: { code: 'V9_ANSWER_REJECTED', message: 'Invalid area value.',
      current_session: { ...start, session_revision: 'd'.repeat(64) } } } });
  });
  await openFixture(page, start);
  await page.getByLabel('Answer value').fill('bad');
  await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect(page.getByRole('complementary', { name: 'AI Copilot' }).getByRole('alert')).toContainText('Invalid area');
  await expect(page.getByLabel('Answer value')).toHaveValue('bad');
  await page.getByRole('button', { name: 'Review and edit answer' }).click();
  await page.getByLabel('Answer value').fill('1');
  await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect.poll(() => calls).toBe(2);
});

test('opt-in actual OSPF browser clarification round trip', async ({ page }) => {
  test.skip(process.env.RUN_LIVE_V9 !== '1', 'Requires local Ollama; creates and updates a real session.');
  test.setTimeout(240_000);
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Configure OSPF on the Penang edge Juniper router');
  const creation = page.waitForResponse((response) => response.url().endsWith('/planning/sessions') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  const initial = await (await creation).json();
  const current = initial.session.pending_questions[0];
  expect(initial.session.status).toBe('needs_clarification');
  expect(current.options.length).toBeGreaterThan(0);
  const form = page.getByRole('form', { name: 'Answer current V9 question' });
  await expect(form).toContainText(current.wording);
  // Choose the actual backend option, not a hard-coded OSPF field or terminal number.
  await form.locator('input[name="v9-option"]').first().check();
  const answerResponse = page.waitForResponse((response) => response.url().endsWith('/answers'));
  await form.getByRole('button', { name: 'Submit answer to V9' }).click();
  const http = await answerResponse;
  expect(http.status()).toBe(200);
  const updated = await http.json();
  expect(updated.accepted).toBe(true);
  expect(updated.answered_question_id).toBe(current.question_id);
  expect(updated.session.session_id).toBe(initial.session.session_id);
  expect(updated.session_revision).not.toBe(initial.session_revision);
  await expect(page.getByText('Answer accepted by V9.', { exact: false })).toBeVisible();
  if (updated.session.pending_questions.length) await expect(form).toContainText(updated.session.pending_questions[0].wording);
  console.log('LIVE_ANSWER', JSON.stringify({ session: updated.session.session_id, question: current.question_id,
    field: current.field_path, option: current.options[0].option_id, status: updated.session.status,
    next: updated.session.pending_questions[0]?.field_path, revision: updated.session_revision }));
});

import { expect, test, type Page } from '@playwright/test';
import type { PlanningResponse, SavedSessionResponse, AnswerRequest } from '../src/services/planningApi';
import { recoveryKey } from '../src/features/chat/recoveryMetadata';

const sessionId = '00000000-0000-4000-8000-000000000071';
const fixture: PlanningResponse = {
  api_version: 1, mode: 'local_v9', inventory_source: 'synthetic', client_request_id: 'creation', session_revision: 'a'.repeat(64),
  session: { session_id: sessionId, status: 'needs_clarification', history: [{ type: 'request', text: 'Configure OSPF on R1 and R2' }],
    plan: { original_prompt: 'Configure OSPF on R1 and R2', status: 'needs_clarification', runtime_authority: 'files',
      knowledge_snapshot_id: '', source_revision: 'historical-source', context_revision: 'historical-inventory', issues: [],
      tasks: ['dev-r1', 'dev-r2'].map((id, index) => ({ intent_id: `intent-ospf:${id}`, logical_intent_id: 'intent-ospf',
        operation_id: 'configure_ospf', device_id: id, status: 'needs_clarification', feedback: '', parameters: {},
        target_refs: [`R${index + 1}`], target_devices: [{ id, hostname: `R${index + 1}`, vendor: index ? 'huawei' : 'cisco', platform: index ? 'vrp' : 'iosxe' }],
        issues: [], configs: [], clarification_history: [], parameter_evidence: {},
      })) },
    pending_questions: [{ question_id: 'q-recover-area', task_id: 'intent-ospf:dev-r1', revision: 3, source_revision: 'historical-source',
      wording: 'Which OSPF area?', field_path: 'area', multiple: false, allow_custom: true, expected_schema: { type: 'string' }, options: [] }],
  },
};

function saved(response = fixture): SavedSessionResponse {
  const { client_request_id: _requestId, ...snapshot } = structuredClone(response);
  void _requestId;
  return { ...snapshot, origin: 'saved_session', freshness: 'not_checked', mutation_eligibility: 'not_checked' };
}

async function create(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Configure OSPF on R1 and R2');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByLabel('Local V9 plan review')).toContainText('configure_ospf');
}

test('explicit reload restore preserves tasks, question IDs and samples; no automatic POST or GET', async ({ page }) => {
  let posts = 0, reads = 0;
  await page.route('**/api/v1/planning/sessions', (route) => { posts++; return route.fulfill({ json: fixture }); });
  await page.route(`**/api/v1/planning/sessions/${sessionId}`, (route) => { reads++; return route.fulfill({ json: saved() }); });
  await create(page);
  const stored = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), recoveryKey);
  expect(stored).toEqual({ reference: { sessionId, revision: fixture.session_revision, answerUncertain: false } });
  await page.reload();
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await expect(page.getByLabel('Saved session ID')).toHaveValue(sessionId);
  expect(reads).toBe(0);
  await page.locator('.view-lines').click();
  await page.keyboard.press('Control+End');
  await page.keyboard.insertText('! RECOVERY-EDIT');
  await page.getByRole('button', { name: 'Restore saved session', exact: true }).click();
  await expect(page.getByRole('listbox', { name: '2 V9 planning tasks' })).toBeVisible();
  await expect(page.getByRole('form', { name: 'Answer current V9 question' })).toContainText('q-recover-area');
  await expect(page.getByLabel('Local V9 plan review')).toContainText('Saved historical state');
  await page.getByRole('option', { name: /intent-ospf:dev-r2/ }).click();
  await expect(page.getByLabel('Task details intent-ospf:dev-r2')).toContainText('huawei');
  await page.getByRole('tab', { name: 'Samples', exact: true }).click();
  await expect(page.locator('.view-lines')).toContainText('RECOVERY-EDIT');
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await page.getByRole('button', { name: 'Clear recovery reference' }).click();
  expect(await page.evaluate((key) => localStorage.getItem(key), recoveryKey)).toBeNull();
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await page.getByLabel('Message the demo Copilot').fill('Recovery is separate');
  await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Recovery is separate”')).toBeVisible();
  expect(posts).toBe(1); expect(reads).toBe(1);
});

test('lost answer response can inspect a matching saved accepted answer without replay', async ({ page }) => {
  let answers = 0;
  let reads = 0;
  const updated = saved();
  await page.route('**/api/v1/planning/sessions', (route) => route.fulfill({ json: fixture }));
  await page.route('**/answers', async (route) => {
    answers++;
    const request: AnswerRequest = route.request().postDataJSON();
    updated.session_revision = 'b'.repeat(64);
    updated.session.plan.tasks[0].parameters = { area: '0' };
    updated.session.plan.tasks[0].clarification_history = [{ answer: request.answer, accepted: true }];
    updated.session.pending_questions[0] = { ...updated.session.pending_questions[0], question_id: 'q-next', wording: 'Which interface?', field_path: 'interfaces' };
    await route.abort('connectionfailed');
  });
  await page.route(`**/api/v1/planning/sessions/${sessionId}`, (route) => {
    reads++;
    return route.fulfill({ json: reads === 1 ? saved() : updated });
  });
  await create(page);
  await page.getByLabel('Answer value').fill('0');
  await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect(page.getByText(/OUTCOME_UNKNOWN:/)).toBeVisible();
  await page.getByRole('button', { name: 'Read latest saved state' }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('Saved revision is unchanged');
  await expect(page.getByLabel('Saved session recovery')).toContainText('Answer outcome remains uncertain');
  await expect(page.getByRole('button', { name: 'Submit answer to V9' })).toBeDisabled();
  await page.getByRole('button', { name: 'Read latest saved state' }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('exact answer as accepted');
  await expect(page.getByRole('form', { name: 'Answer current V9 question' })).toContainText('q-next');
  await expect(page.getByLabel('Task details intent-ospf:dev-r1')).toContainText('area');
  expect(answers).toBe(1);
});

test('changed revision without matching evidence stays uncertain across reload and blocks answers', async ({ page }) => {
  let answers = 0;
  const updated = saved(); updated.session_revision = 'c'.repeat(64);
  await page.route('**/api/v1/planning/sessions', (route) => route.fulfill({ json: fixture }));
  await page.route('**/answers', (route) => { answers++; return route.abort('connectionfailed'); });
  await page.route(`**/api/v1/planning/sessions/${sessionId}`, (route) => route.fulfill({ json: updated }));
  await create(page);
  await page.getByLabel('Answer value').fill('0');
  await page.getByRole('button', { name: 'Submit answer to V9' }).click();
  await expect(page.getByText(/OUTCOME_UNKNOWN:/)).toBeVisible();
  await page.getByRole('button', { name: 'Read latest saved state' }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('Saved revision has changed');
  await expect(page.getByLabel('Saved session recovery')).toContainText('Answer outcome remains uncertain');
  await expect(page.getByRole('button', { name: 'Submit answer to V9' })).toBeDisabled();
  await page.getByLabel('Saved session ID').fill('bad-id');
  await page.getByRole('button', { name: 'Restore saved session', exact: true }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('Enter a valid session UUID');
  await expect(page.getByRole('button', { name: 'Submit answer to V9' })).toBeDisabled();
  await page.getByRole('button', { name: 'Clear recovery reference' }).click();
  await page.getByRole('button', { name: 'Read latest saved state' }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('Answer outcome remains uncertain');
  await page.reload();
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByRole('button', { name: 'Restore saved session', exact: true }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('Answer outcome remains uncertain');
  expect(answers).toBe(1);
});

test('missing, incompatible and unavailable reads retain current plan and never replay', async ({ page }) => {
  let reads = 0;
  await page.route('**/api/v1/planning/sessions', (route) => route.fulfill({ json: fixture }));
  await page.route(`**/api/v1/planning/sessions/${sessionId}`, (route) => {
    reads++;
    if (reads === 3) return route.abort('connectionfailed');
    return route.fulfill({ status: reads === 1 ? 404 : 409, json: { detail: {
      code: reads === 1 ? 'SESSION_NOT_FOUND' : 'UNSUPPORTED_SESSION_VERSION', message: 'Cannot restore this saved session.',
    } } });
  });
  await create(page);
  for (const message of ['SESSION_NOT_FOUND', 'UNSUPPORTED_SESSION_VERSION', 'Saved session is unavailable']) {
    await page.getByRole('button', { name: 'Read latest saved state' }).click();
    await expect(page.getByLabel('Saved session recovery').getByRole('alert')).toContainText(message);
    await expect(page.getByLabel('Task details intent-ospf:dev-r1')).toBeVisible();
  }
});

test('unknown creation ID survives reload as unresolved and does not restore an older session', async ({ page }) => {
  let posts = 0, gets = 0;
  await page.route('**/api/v1/planning/sessions', (route) => { posts++; return route.abort('connectionfailed'); });
  await page.route('**/api/v1/planning/sessions/*', (route) => { gets++; return route.abort(); });
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Create a new plan');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('Check the durable receipt without replaying creation');
  await page.reload();
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('session ID was not confirmed');
  await expect(page.getByRole('button', { name: 'Restore saved session', exact: true })).toBeDisabled();
  expect(posts).toBe(1); expect(gets).toBe(0);
});

test('creation-only UUID recovers after simulated restart without replay and preserves workbench', async ({ page }) => {
  let posts = 0, gets = 0, lookups = 0;
  let requestId = '';
  await page.route('**/api/v1/planning/sessions', (route) => {
    posts++; requestId = route.request().postDataJSON().client_request_id;
    return route.abort('connectionfailed');
  });
  await page.route('**/api/v1/planning/requests/*', (route) => {
    lookups++;
    expect(route.request().method()).toBe('GET');
    expect(route.request().url()).toContain(requestId);
    return route.fulfill({ json: { api_version: 1, client_request_id: requestId, status: 'completed',
      session_id: sessionId, session_revision: fixture.session_revision, error_code: null, message: 'Creation is recorded.' } });
  });
  await page.route(`**/api/v1/planning/sessions/${sessionId}`, (route) => { gets++; return route.fulfill({ json: saved() }); });
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Configure OSPF on R1 and R2');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByText(/outcome is unknown/)).toBeVisible();
  const stored = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), recoveryKey);
  expect(stored).toEqual({ unknownCreationRequestId: requestId });
  // Routes model a fresh backend retaining only the durable association/session.
  await page.reload();
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  expect(lookups).toBe(0); expect(gets).toBe(0);
  await page.locator('.view-lines').click();
  await page.keyboard.press('Control+End');
  await page.keyboard.insertText('! RECEIPT-RECOVERY');
  await page.getByRole('button', { name: 'Check creation outcome' }).click();
  await expect(page.getByLabel('Local V9 plan review')).toContainText('Saved historical state');
  await expect(page.getByRole('listbox', { name: '2 V9 planning tasks' })).toBeVisible();
  await expect(page.getByRole('form', { name: 'Answer current V9 question' })).toContainText('q-recover-area');
  expect(posts).toBe(1); expect(lookups).toBe(1); expect(gets).toBe(1);
  expect(await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), recoveryKey))
    .toEqual({ reference: { sessionId, revision: fixture.session_revision, answerUncertain: false } });
  await page.getByRole('tab', { name: 'Samples', exact: true }).click();
  await expect(page.locator('.view-lines')).toContainText('RECEIPT-RECOVERY');
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await page.getByLabel('Message the demo Copilot').fill('Receipt recovery is separate');
  await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Receipt recovery is separate”')).toBeVisible();
});

test('outcome states and invalid saved result never adopt an unrelated remembered session', async ({ page }) => {
  const requestId = '00000000-0000-4000-8000-000000000081';
  let posts = 0, reads = 0;
  let status = 'in_progress';
  let release: () => void = () => {};
  let gate: Promise<void> | undefined = new Promise((resolve) => { release = resolve; });
  await page.addInitScript(({ key, id, requestId }) => localStorage.setItem(key, JSON.stringify({
    unknownCreationRequestId: requestId, reference: { sessionId: id, revision: 'a'.repeat(64), answerUncertain: false },
  })), { key: recoveryKey, id: sessionId, requestId });
  await page.route('**/api/v1/planning/sessions', (route) => { posts++; return route.abort(); });
  await page.route('**/api/v1/planning/sessions/*', (route) => { reads++; return route.fulfill({ json: { origin: 'invalid' } }); });
  await page.route('**/api/v1/planning/requests/*', async (route) => {
    if (gate) await gate;
    if (status === 'unavailable') return route.abort('connectionfailed');
    return route.fulfill({ json: { api_version: 1, client_request_id: requestId, status,
      session_id: status === 'completed' ? sessionId : null, session_revision: status === 'completed' ? 'a'.repeat(64) : null,
      error_code: null, message: `Recorded status: ${status}. No automatic replay.` } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByRole('button', { name: 'Check creation outcome' }).click();
  await expect(page.getByRole('button', { name: 'Check creation outcome' })).toBeDisabled();
  release(); gate = undefined;
  await expect(page.getByLabel('Saved session recovery')).toContainText('Creation outcome: in_progress');
  for (const next of ['unknown', 'indeterminate', 'corrupt', 'terminal_error']) {
    status = next;
    await page.getByRole('button', { name: 'Check creation outcome' }).click();
    await expect(page.getByLabel('Saved session recovery')).toContainText(`Creation outcome: ${next}`);
    await expect(page.getByLabel('Local V9 plan review')).toHaveCount(0);
  }
  expect(reads).toBe(0);
  status = 'completed';
  await page.getByRole('button', { name: 'Check creation outcome' }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('Invalid saved-session response');
  await expect(page.getByText(requestId, { exact: true })).toBeVisible();
  status = 'unavailable';
  await page.getByRole('button', { name: 'Check creation outcome' }).click();
  await expect(page.getByLabel('Saved session recovery')).toContainText('lookup is unavailable');
  expect(posts).toBe(0); expect(reads).toBe(1);
  await expect(page.locator('.monaco-editor')).toBeVisible();
});

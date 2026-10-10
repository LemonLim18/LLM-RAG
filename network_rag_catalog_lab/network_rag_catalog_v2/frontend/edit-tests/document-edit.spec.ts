import { expect, test, type Page, type Route } from '@playwright/test';
import { createHash, randomUUID } from 'node:crypto';
import { fixture, initial, buffer, edit, open, reviewReady, proposal, stage, snapshot, idFor } from '../review-tests/helpers';

const prompt = 'Change VLAN 100 name from SALES to ENGINEERING';
const endpoint = '**/api/v1/workbench/working-documents/*/propose-edit';
function response(route: Route, overrides: object = {}) {
  const body = route.request().postDataJSON();
  return { api_version: 1, document_id: route.request().url().split('/').at(-2), base_revision: body.expected_revision,
    base_content_sha256: createHash('sha256').update(body.current_content).digest('hex'), proposal_id: randomUUID(), outcome: 'proposal',
    proposed_content: body.current_content.replace('SALES', 'ENGINEERING'), message: 'Controlled model response · V9 bounded operation only',
    operation_id: 'rename_vlan', parameters: { vlan_id: 100, new_vlan_name: 'ENGINEERING' }, evidence: {},
    authority: { runtime: 'direct_files', model: 'test double' }, validation: 'bounded_operation_only', deployment: 'not_deployed', ...overrides };
}
async function mode(page: Page) { await page.getByRole('button', { name: 'Edit active file', exact: true }).click(); }
async function send(page: Page, text = prompt) {
  await page.getByLabel('Instruct Local V9 to edit active file').fill(text);
  await page.getByRole('button', { name: 'Propose edit with Local V9', exact: true }).click();
}
async function setup(page: Page) {
  const data = await fixture(page);
  await page.route(endpoint, (route) => route.fulfill({ json: response(route) }));
  await mode(page); return data;
}

test('active file context, real Monaco review, accept without save, then explicit Ctrl+S', async ({ page }) => {
  const { mutations } = await setup(page); await send(page); await reviewReady(page);
  expect(await buffer(page)).toBe(initial);
  expect(mutations).toHaveLength(1);
  await expect(page.getByLabel('Local V9 document editing')).toContainText(idFor());
  await page.getByRole('button', { name: 'Accept Changes' }).click();
  expect(await buffer(page)).toBe(initial.replace('SALES', 'ENGINEERING')); expect(mutations).toHaveLength(1);
  await page.keyboard.press('Control+s'); await expect.poll(() => mutations.length).toBe(2);
  expect(mutations[1]).toContain('PUT');
});
test('reject retains accepted and saved text without mutation', async ({ page }) => {
  const { mutations } = await setup(page); await send(page); await reviewReady(page);
  await page.getByRole('button', { name: 'Reject Changes' }).click(); expect(await buffer(page)).toBe(initial);
  expect(mutations).toHaveLength(1);
});
test('pending UI prevents duplicate requests without blocking Monaco edits', async ({ page }) => {
  await setup(page); let resolve!: () => void; const wait = new Promise<void>((r) => { resolve = r; }); let calls = 0;
  await page.route(endpoint, async (route) => { calls++; await wait; await route.fulfill({ json: response(route) }); });
  await send(page); await expect(page.getByRole('button', { name: 'Propose edit with Local V9' })).toBeDisabled();
  await expect(page.getByLabel('Local V9 document editing')).toContainText('interpreting');
  await edit(page, initial + '! typed while pending\n'); resolve();
  await expect(page.getByLabel('Local V9 document editing').getByRole('alert')).toBeVisible();
  expect(calls).toBe(1); expect(await buffer(page)).toContain('typed while pending');
});
test('current unsaved content is sent, unrelated bytes preserved', async ({ page }) => {
  await setup(page); const current = initial + '! manual trailing note\n'; await edit(page, current);
  let captured = ''; await page.route(endpoint, (route) => { captured = route.request().postDataJSON().current_content; return route.fulfill({ json: response(route) }); });
  await send(page); await reviewReady(page); expect(captured).toBe(current);
  await page.getByRole('button', { name: 'Accept Changes' }).click(); expect(await buffer(page)).toBe(current.replace('SALES', 'ENGINEERING'));
});
test('second accepted edit uses latest buffer rather than original or last save', async ({ page }) => {
  await setup(page); await send(page); await reviewReady(page); await page.getByRole('button', { name: 'Accept Changes' }).click();
  let captured = ''; await page.route(endpoint, (route) => { captured = route.request().postDataJSON().current_content; return route.fulfill({ json: response(route, { proposed_content: captured.replace('ENGINEERING', 'FINANCE') }) }); });
  await send(page, 'Rename VLAN 100 to FINANCE'); await reviewReady(page); expect(captured).toContain('ENGINEERING');
  await page.getByRole('button', { name: 'Accept Changes' }).click(); expect(await buffer(page)).toBe(initial.replace('SALES', 'FINANCE'));
});
for (const outcome of ['clarification_required', 'unsupported', 'no_change'] as const) {
  test(`${outcome} is honest and does not fabricate a change`, async ({ page }) => {
    const { mutations } = await setup(page);
    await page.route(endpoint, (route) => route.fulfill({ json: response(route, { outcome, proposed_content: outcome === 'no_change' ? initial : null, message: outcome + ' · no edit applied' }) }));
    await send(page); await expect(page.getByLabel('Local V9 document editing')).toContainText(outcome === 'no_change' ? 'No changes' : outcome);
    await expect(page.getByLabel('Pending change proposal')).toHaveCount(0); expect(await buffer(page)).toBe(initial); expect(mutations).toHaveLength(1);
  });
}
for (const code of ['STALE_WORKING_REVISION', 'EDIT_TARGET_CONFLICT', 'LOCAL_MODEL_UNAVAILABLE', 'INVALID_EDIT_PARAMETERS']) {
  test(`${code} does not modify the working file`, async ({ page }) => {
    const { mutations } = await setup(page); await page.route(endpoint, (route) => route.fulfill({ status: 409, json: { detail: { code, message: 'Safe failure' } } }));
    await send(page); await expect(page.getByLabel('Local V9 document editing').getByRole('alert')).toContainText(code);
    expect(await buffer(page)).toBe(initial); expect(mutations).toHaveLength(1);
  });
}
test('lost response is explicit, no POST retry or implicit save', async ({ page }) => {
  const { mutations } = await setup(page); await page.route(endpoint, (route) => route.abort('failed'));
  await send(page); await expect(page.getByLabel('Local V9 document editing').getByRole('alert')).toContainText('No automatic retry');
  expect(mutations).toHaveLength(1); expect(await buffer(page)).toBe(initial);
});
test('wrong response identity is refused', async ({ page }) => {
  await setup(page); await page.route(endpoint, (route) => route.fulfill({ json: response(route, { document_id: idFor(2) }) }));
  await send(page); await expect(page.getByLabel('Local V9 document editing').getByRole('alert')).toContainText('INVALID_EDIT_RESPONSE');
  await expect(page.getByLabel('Pending change proposal')).toHaveCount(0);
});
for (const change of ['file', 'mode', 'aba', 'save'] as const) {
  test(`late response after ${change} is refused`, async ({ page }) => {
    await setup(page); let release!: () => void; let entered!: () => void;
    const started = new Promise<void>((r) => { entered = r; }); const wait = new Promise<void>((r) => { release = r; });
    await page.route(endpoint, async (route) => { entered(); await wait; await route.fulfill({ json: response(route) }); });
    await send(page); await started;
    if (change === 'file') { await open(page, 2); await open(page, 1); }
    if (change === 'mode') { await page.getByRole('button', { name: 'Demo mock', exact: true }).click(); await mode(page); }
    if (change === 'aba') { await edit(page, initial + 'A'); await edit(page, initial); }
    if (change === 'save') { await page.keyboard.press('Control+s'); await expect.poll(async () => (await snapshot(page)).tabs[idFor()].saved.save_sequence).toBe(1); }
    release(); await expect(page.getByLabel('Local V9 document editing').getByRole('alert')).toBeVisible();
    await expect(page.getByLabel('Pending change proposal')).toHaveCount(0); expect(await buffer(page)).toBe(initial);
  });
}
test('existing pending proposal is never replaced by a new request', async ({ page }) => {
  const { mutations } = await setup(page); await stage(page, await proposal(page, initial + '! existing'));
  await reviewReady(page); await expect(page.getByRole('button', { name: 'Propose edit with Local V9' })).toBeDisabled();
  expect(mutations).toHaveLength(0);
});
test('sample and original selections disable editing; Demo and planning remain separate', async ({ page }) => {
  const { mutations } = await setup(page);
  await page.getByRole('button', { name: /^Open saved original R1 / }).click();
  await expect(page.getByRole('button', { name: 'Propose edit with Local V9' })).toBeDisabled();
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await page.getByLabel('Message the demo Copilot').fill('hello'); await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('hello', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Restore saved session', exact: true })).toBeVisible();
  await expect(page.getByLabel('Request a Local V9 plan')).toBeEnabled(); expect(mutations).toHaveLength(0);
});

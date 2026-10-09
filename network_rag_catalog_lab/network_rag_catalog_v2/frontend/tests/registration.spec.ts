import { expect, test, type Page } from '@playwright/test';
import type { InventoryDevice, InventoryListResponse } from '../src/services/inventoryApi';

async function fillDevice(page: Page) {
  await page.getByRole('button', { name: 'Add Device', exact: true }).click();
  await page.getByLabel('Hostname', { exact: true }).fill('R99');
  await page.getByLabel('Display name', { exact: true }).fill('Demo router 99');
  await page.getByLabel('Software version').fill('23.4');
  await page.getByLabel('Site', { exact: true }).fill('Lab');
  await page.getByLabel('Role', { exact: true }).fill('edge');
  await page.getByLabel('Vendor / platform').selectOption('juniper');
  await page.getByRole('checkbox', { name: 'ospf', exact: true }).check();
}

test('registration validates, saves once, reloads/selects and preserves plan, samples and mock mode', async ({ page }) => {
  let calls = 0, gets = 0;
  let added: InventoryDevice | undefined;
  let release: () => void = () => {};
  const pending = new Promise<void>((resolve) => { release = resolve; });
  await page.route('**/api/v1/inventory/devices', async (route) => {
    if (route.request().method() === 'POST') {
      calls++;
      const request = route.request().postDataJSON();
      expect(request.expected_inventory_revision).toMatch(/^[a-f0-9]{64}$/);
      expect(request.device.interfaces[0]).toMatchObject({ name: 'ge-0/0/0', role: 'uplink', enabled: false });
      expect(request.device).not.toHaveProperty('management_ip');
      added = { ...request.device, id: 'dev-registration-test', status: null,
        interfaces: request.device.interfaces.map((item: object) => ({ ...item, neighbor: null })) };
      await pending;
      return route.fulfill({ status: 201, json: { api_version: 1, source: 'synthetic', inventory_revision: 'b'.repeat(64), device: added } });
    }
    gets++;
    const response = await route.fetch();
    const body: InventoryListResponse = await response.json();
    if (added) { body.devices.push(added); body.inventory_revision = 'b'.repeat(64); }
    return route.fulfill({ json: body });
  });
  await page.route('**/api/v1/planning/sessions', (route) => route.fulfill({ json: {
    api_version: 1, mode: 'local_v9', inventory_source: 'synthetic', client_request_id: route.request().postDataJSON().client_request_id,
    session_revision: 'a'.repeat(64), session: { session_id: '00000000-0000-4000-8000-000000000099', status: 'ready',
      plan: { original_prompt: 'Sample session', status: 'ready', runtime_authority: 'files', knowledge_snapshot_id: '', issues: [],
        tasks: [{ intent_id: 'keep-task', operation_id: 'create_vlan', status: 'ready', device_id: 'dev-r1', parameters: { vlan_id: 100 }, target_devices: [], target_refs: ['R1'], issues: [], configs: [], feedback: '' }] }, pending_questions: [] },
  } }));
  await page.goto('/');
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await page.locator('.view-lines').click(); await page.keyboard.press('Control+End'); await page.keyboard.insertText('! REGISTER-KEEP');
  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Sample session');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByLabel('Task details keep-task')).toBeVisible();
  await page.getByRole('button', { name: 'Add Device', exact: true }).click();
  await page.getByRole('button', { name: 'Register synthetic device', exact: true }).click();
  expect(calls).toBe(0);
  await page.getByRole('button', { name: 'Close registration' }).click();
  await fillDevice(page);
  await page.getByRole('checkbox', { name: 'ospf', exact: true }).uncheck();
  await page.getByRole('button', { name: 'Register synthetic device', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Select at least one');
  await page.getByRole('checkbox', { name: 'ospf', exact: true }).check();
  await page.getByRole('button', { name: 'Add initial interface' }).click();
  await page.getByLabel('Interface 1 name', { exact: true }).fill('ge-0/0/0');
  await page.getByLabel('Interface 1 role').fill('uplink');
  await page.getByRole('button', { name: 'Register synthetic device', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Saving / loading…' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Close registration' })).toBeDisabled();
  release();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('listitem', { name: /R99 Juniper/ })).toHaveAttribute('aria-current', 'true');
  await expect(page.getByLabel('Local V9 plan review')).toContainText('Saved historical state');
  await expect(page.getByLabel('Task details keep-task')).toBeVisible();
  await page.getByRole('tab', { name: 'Samples', exact: true }).click();
  await expect(page.locator('.view-lines')).toContainText('REGISTER-KEEP');
  expect(calls).toBe(1); expect(gets).toBeGreaterThanOrEqual(2);
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await page.getByLabel('Message the demo Copilot').fill('Keep demo separate');
  await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Keep demo separate”')).toBeVisible();
});

test('duplicate and stale revision errors retain input and require explicit refresh', async ({ page }) => {
  const revisions: string[] = [];
  await page.route('**/api/v1/inventory/devices', async (route) => {
    if (route.request().method() === 'POST') {
      revisions.push(route.request().postDataJSON().expected_inventory_revision);
      return route.fulfill({ status: 409, json: { detail: { code: revisions.length === 1 ? 'IDENTITY_CONFLICT' : 'STALE_INVENTORY', message: 'Review input and current inventory.' } } });
    }
    const body = await (await route.fetch()).json();
    body.inventory_revision = (revisions.length === 0 ? 'a' : 'b').repeat(64);
    return route.fulfill({ json: body });
  });
  await page.goto('/'); await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await fillDevice(page);
  await page.getByRole('button', { name: 'Register synthetic device', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('IDENTITY_CONFLICT');
  await page.getByLabel('Hostname', { exact: true }).fill('R100');
  await page.getByRole('button', { name: 'Register synthetic device', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('STALE_INVENTORY');
  await expect(page.getByRole('button', { name: 'Register synthetic device', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reload inventory revision' }).click();
  await expect(page.getByRole('dialog').getByRole('status')).toContainText('Inventory reloaded');
  await expect(page.getByLabel('Hostname', { exact: true })).toHaveValue('R100');
  await page.getByText('Expected inventory revision', { exact: true }).click();
  await expect(page.getByRole('dialog').locator('code')).toHaveText('b'.repeat(64));
  expect(revisions).toEqual(['a'.repeat(64), 'a'.repeat(64)]);
});

test('lost response is not auto-replayed and confirmed-save reload failure offers only reload', async ({ page }) => {
  let posts = 0, failReads = false;
  await page.route('**/api/v1/inventory/devices', async (route) => {
    if (route.request().method() === 'POST') {
      posts++;
      if (posts === 1) return route.abort('connectionfailed');
      failReads = true;
      return route.fulfill({ status: 201, json: { api_version: 1, source: 'synthetic', inventory_revision: 'c'.repeat(64),
        device: { ...route.request().postDataJSON().device, id: 'dev-new' } } });
    }
    if (failReads) return route.abort('connectionfailed');
    return route.continue();
  });
  await page.goto('/'); await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await fillDevice(page);
  await page.getByRole('button', { name: 'Register synthetic device', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('OUTCOME_UNKNOWN');
  await expect(page.getByRole('button', { name: 'Register synthetic device', exact: true })).toBeDisabled();
  expect(posts).toBe(1);
  await page.getByRole('button', { name: 'Reload inventory revision' }).click();
  await expect(page.getByRole('dialog').getByRole('status')).toContainText('Inventory reloaded');
  await page.getByRole('button', { name: 'Register synthetic device', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Registration succeeded, but inventory reload failed');
  await expect(page.getByRole('button', { name: 'Register synthetic device', exact: true })).toBeDisabled();
  expect(posts).toBe(2);
});

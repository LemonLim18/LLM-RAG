import { expect, test } from '@playwright/test';

test('renders the four-region shell and retains Monaco edits per tab', async ({ page }) => {
  const outsideRequests: string[] = [];
  const pageErrors: string[] = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) outsideRequests.push(request.url());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));

  await page.goto('/');
  await expect(page.getByRole('complementary', { name: 'Infrastructure explorer' })).toBeVisible();
  await expect(page.getByRole('main', { name: 'Configuration workspace' })).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'AI Copilot' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Simulated activity and output' })).toBeVisible();
  await expect(page.getByText('LOCAL PREVIEW · SYNTHETIC INVENTORY · SAMPLE EDITS RESET ON RELOAD')).toBeVisible();
  await expect(page.getByRole('status')).toContainText('Backend connected · Direct files');
  await expect(page.getByText('AI not checked')).toBeVisible();
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await expect(page.getByText(/V9 demo inventory · API/)).toBeVisible();

  const inventoryResponse = await page.request.get('/api/v1/inventory/devices');
  expect(inventoryResponse.status()).toBe(200);
  const inventory = await inventoryResponse.json();
  expect(inventory.source).toBe('synthetic');
  expect(inventory.devices.find((device: { id: string }) => device.id === 'dev-r1')).toMatchObject({ hostname: 'R1', vendor: 'cisco' });
  const unknownDevice = await page.request.get('/api/v1/inventory/devices/missing-device');
  expect(unknownDevice.status()).toBe(404);
  expect((await unknownDevice.json()).detail.code).toBe('DEVICE_NOT_FOUND');

  const editor = page.locator('.monaco-editor');
  await expect(editor).toBeVisible({ timeout: 20_000 });
  await page.locator('.view-lines').click();
  await page.keyboard.press('Control+End');
  await page.keyboard.press('Enter');
  await page.keyboard.insertText('! TEST-MARKER');
  await expect(page.locator('.view-lines')).toContainText('TEST-MARKER');

  await page.getByRole('tab', { name: /r2-huawei\.cfg/i }).click();
  await expect(page.locator('.view-lines')).toContainText('sysname R2');
  await expect(page.locator('.view-lines')).not.toContainText('TEST-MARKER');
  await page.getByRole('tab', { name: /r1-cisco\.cfg/i }).click();
  await expect(page.locator('.view-lines')).toContainText('TEST-MARKER');

  await page.getByRole('listitem', { name: /R3 Juniper/i }).click();
  await expect(page.getByText('Edge Router 1')).toBeVisible();
  await expect(page.getByText('junos 23.4 · Branch Campus')).toBeVisible();
  await expect(page.getByText('edge', { exact: true })).toBeVisible();
  await expect(page.locator('.view-lines')).toContainText('host-name R3');

  await page.getByLabel('Filter V9 demo inventory devices').fill('huawei');
  await expect(page.getByRole('listitem', { name: /R2 Huawei/i })).toBeVisible();
  await expect(page.getByRole('listitem', { name: /SW2 Huawei/i })).toBeVisible();
  await expect(page.getByRole('listitem', { name: /R1 Cisco/i })).toHaveCount(0);

  await page.getByLabel('Message the demo Copilot').fill('Prepare a safe preview');
  await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Prepare a safe preview”')).toBeVisible();

  const separator = page.getByRole('separator', { name: 'Resize infrastructure explorer' });
  const before = Number(await separator.getAttribute('aria-valuenow'));
  await separator.focus();
  await page.keyboard.press('ArrowRight');
  await expect(separator).toHaveAttribute('aria-valuenow', String(before + 12));
  expect(outsideRequests).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test('remains usable at the supported compact desktop viewport', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('/');
  await expect(page.getByRole('main', { name: 'Configuration workspace' })).toBeVisible();
  await expect(page.locator('.monaco-editor')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole('complementary', { name: 'AI Copilot' })).toBeVisible();
});

test('stays usable and offers retry when the backend is unavailable', async ({ page }) => {
  await page.route('**/api/v1/**', (route) => route.abort('connectionfailed'));
  await page.goto('/');

  await expect(page.getByRole('status')).toContainText('Backend unavailable');
  await expect(page.getByRole('button', { name: 'Retry backend connection' })).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Infrastructure explorer' }).getByRole('alert')).toContainText('V9 demo inventory is unavailable');
  await expect(page.getByRole('button', { name: 'Retry inventory' })).toBeVisible();
  await expect(page.locator('.monaco-editor')).toBeVisible({ timeout: 20_000 });
  await page.getByLabel('Message the demo Copilot').fill('Still local');
  await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Still local”')).toBeVisible();
});

import { expect, test } from '@playwright/test';

test('real GUI registration persists through FastAPI into isolated V9 inventory', async ({ page, request }) => {
  await page.goto('/');
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await page.getByRole('button', { name: 'Add Device', exact: true }).click();
  for (const [label, value] of [['Hostname', 'R199'], ['Display name', 'Synthetic router 199'], ['Software version', '23.4'], ['Site', 'Lab'], ['Role', 'edge']]) {
    await page.getByLabel(label, { exact: true }).fill(value);
  }
  await page.getByLabel('Vendor / platform').selectOption('juniper');
  await page.getByRole('checkbox', { name: 'ospf', exact: true }).check();
  await page.getByRole('button', { name: 'Add initial interface' }).click();
  await page.getByLabel('Interface 1 name', { exact: true }).fill('ge-0/0/0');
  await page.getByLabel('Interface 1 role').fill('management');
  const saved = page.waitForResponse((response) => response.url().endsWith('/inventory/devices') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Register synthetic device', exact: true }).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const body = await response.json();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('listitem', { name: /R199 Juniper/ })).toHaveAttribute('aria-current', 'true');
  const detail = await request.get(`/api/v1/inventory/devices/${body.device.id}`);
  expect(await detail.json()).toEqual(body);
  await page.reload();
  await expect(page.getByLabel('7 demo inventory devices')).toBeVisible();
  await page.getByRole('listitem', { name: /R199 Juniper/ }).click();
  await expect(page.getByText('1 interfaces', { exact: true })).toBeVisible();
});

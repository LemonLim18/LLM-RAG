import { expect, test } from '@playwright/test';

const task = (id: string, intent: string, device: { id: string; hostname: string; vendor: string; platform: string }, status: string, configuration = '') => ({
  intent_id: id, logical_intent_id: intent, request_text: `Configure service for ${device.hostname}`, category: 'routing',
  operation_id: intent === 'intent-ospf' ? 'configure_ospf' : 'create_vlan', device_id: device.id, status, feedback: '',
  parameters: intent === 'intent-ospf' ? { area: '0.0.0.0', interfaces: [{ name: 'GigabitEthernet0/0' }] } : { vlan_id: 200 },
  parameter_provenance: intent === 'intent-ospf' ? { area: 'user', interfaces: 'context:inventory' } : { vlan_id: 'user' },
  parameter_evidence: intent === 'intent-ospf'
    ? { area: { source: 'user', evidence: 'area 0', validation: status === 'rendered' ? 'valid' : 'blocked' } }
    : { vlan_id: { source: 'user', evidence: 'VLAN 200', validation: 'valid' } },
  target_refs: [device.hostname], target_devices: [device], target_resolution: [], revision: 1, source_revision: 'source-fixture',
  planning_issues: [], issues: status === 'needs_clarification' ? [{ type: 'MISSING', field: 'interfaces[0].area', message: 'Area is required.' }] : [],
  configs: configuration ? [{ ...device, configuration }] : [],
});

const r1 = { id: 'dev-r1', hostname: 'R1', vendor: 'cisco', platform: 'iosxe' };
const r2 = { id: 'dev-r2', hostname: 'R2', vendor: 'huawei', platform: 'vrp' };
const r3 = { id: 'dev-r3', hostname: 'R3', vendor: 'juniper', platform: 'junos' };

function sessionFixture(sessionId: string, tasks = [
  task('intent-ospf:dev-r1', 'intent-ospf', r1, 'rendered', 'router ospf 10\n network 10.0.0.0 0.0.0.255 area 0'),
  task('intent-ospf:dev-r2', 'intent-ospf', r2, 'rendered', 'ospf 10\n area 0.0.0.0'),
  task('intent-vlan:dev-r3', 'intent-vlan', r3, 'needs_clarification'),
]) {
  return {
    api_version: 1, mode: 'local_v9', inventory_source: 'synthetic', client_request_id: 'replaced-by-route', session_revision: 'e'.repeat(64),
    session: { session_id: sessionId, status: 'needs_clarification',
      plan: { original_prompt: 'Configure OSPF on R1 and R2, then VLAN 200 on R3', status: 'needs_clarification', runtime_authority: 'files', knowledge_snapshot_id: '', issues: [],
        intents: [
          { intent_id: 'intent-ospf', request_text: 'Configure OSPF on R1 and R2', target_refs: ['R1', 'R2'], target_text: 'R1 and R2', source_spans: [], issues: [] },
          { intent_id: 'intent-vlan', request_text: 'Create VLAN 200 on R3', target_refs: ['R3'], target_text: 'R3', source_spans: [], issues: [] },
        ], tasks },
      pending_questions: tasks.length === 3 ? [{ question_id: 'q-area-r3', task_id: 'intent-vlan:dev-r3', revision: 1, source_revision: 'source-fixture', wording: 'Which area should R3 use?', field_path: 'interfaces[0].area', multiple: false, allow_custom: true, expected_schema: { type: 'string' }, options: [] }] : [],
    },
  };
}

test('reviews multi-intent device tasks without replacing sample Monaco documents', async ({ page }) => {
  let creation = 0;
  await page.route('**/api/v1/planning/sessions', async (route) => {
    const request = route.request().postDataJSON();
    creation += 1;
    const response = creation === 1
      ? sessionFixture('00000000-0000-4000-8000-000000000061')
      : sessionFixture('00000000-0000-4000-8000-000000000062', [task('intent-new:dev-r3', 'intent-new', r3, 'rendered', 'set system host-name R3')]);
    await route.fulfill({ json: { ...response, client_request_id: request.client_request_id } });
  });
  await page.goto('/');

  await page.locator('.view-lines').click();
  await page.keyboard.press('Control+End');
  await page.keyboard.press('Enter');
  await page.keyboard.insertText('! REVIEW-MARKER');

  await page.getByRole('button', { name: 'Local V9', exact: true }).click();
  await page.getByLabel('Request a Local V9 plan').fill('Configure OSPF on R1 and R2, then VLAN 200 on R3');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();

  const review = page.getByLabel('Local V9 plan review');
  await expect(review).toContainText('2 intent(s)');
  await expect(page.getByRole('listbox', { name: '3 V9 planning tasks' }).getByRole('option')).toHaveCount(3);
  await expect(page.getByLabel('Task details intent-ospf:dev-r1')).toContainText('router ospf 10');
  await expect(page.getByLabel('Task details intent-ospf:dev-r1').locator('.task-identity-grid')).toContainText('intent-ospf');

  await page.getByRole('option', { name: /intent-ospf:dev-r2/ }).click();
  const r2Details = page.getByLabel('Task details intent-ospf:dev-r2');
  await expect(r2Details).toContainText('R2');
  await expect(r2Details).toContainText('huawei · vrp');
  await expect(r2Details).toContainText('ospf 10');
  await expect(r2Details).not.toContainText('router ospf 10');
  await expect(r2Details.getByLabel('Extracted parameters')).toContainText('context:inventory');
  await expect(r2Details.getByLabel('Extracted parameters')).not.toContainText('VLAN 200');

  await page.getByRole('option', { name: /intent-vlan:dev-r3/ }).click();
  const blocked = page.getByLabel('Task details intent-vlan:dev-r3');
  await expect(blocked.locator('[data-v9-status="needs_clarification"]')).toContainText('Clarification required');
  await expect(blocked).toContainText('Area is required.');
  await expect(blocked).toContainText('Which area should R3 use?');
  await expect(blocked).toContainText('No generated configuration is present');

  await page.getByLabel('Request a Local V9 plan').fill('Configure a replacement session on R3');
  await page.getByRole('button', { name: 'Create Local V9 session' }).click();
  await expect(page.getByRole('listbox', { name: '1 V9 planning tasks' }).getByRole('option')).toHaveCount(1);
  await expect(page.getByLabel('Task details intent-new:dev-r3')).toBeVisible();
  await expect(page.getByLabel('Task details intent-vlan:dev-r3')).toHaveCount(0);

  await page.getByRole('tab', { name: 'Samples' }).click();
  await expect(page.locator('.view-lines')).toContainText('REVIEW-MARKER');
  await expect(page.getByLabel('6 demo inventory devices')).toBeVisible();
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click();
  await page.getByLabel('Message the demo Copilot').fill('Review remains separate');
  await page.getByRole('button', { name: 'Send demo message' }).click();
  await expect(page.getByText('Mock response: I received “Review remains separate”')).toBeVisible();
});

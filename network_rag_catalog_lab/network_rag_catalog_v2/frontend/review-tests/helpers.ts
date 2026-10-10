import { expect, type Page } from '@playwright/test';
import type { WorkingDocument } from '../src/services/workingApi';
import type { ChangeProposal } from '../src/features/workspace/changeReview';
import type {} from '../review-harness/ReviewHarness';

export const initial = 'vlan 100\n name SALES\n';
export const workingUrl = '**/api/v1/workbench/working-documents';
export const idFor = (n = 1) => 'working-' + String(n).repeat(64);
export function record(n = 1, content = initial): WorkingDocument {
  return { schema_version: 1, document_id: idFor(n), revision: `00000000-0000-4000-8000-00000000000${n}`, save_sequence: 0,
    created_at: '2026-10-10T00:00:00Z', updated_at: '2026-10-10T00:00:00Z', content_sha256: 'e'.repeat(64), encoding: 'utf-8',
    validation: 'unvalidated', deployment: 'not_deployed', content, record_sha256: 'f'.repeat(64),
    original: { schema_version: 1, kind: 'generated_original', artifact_id: 'original-' + String(n).repeat(64),
      source: { session_id: '00000000-0000-4000-8000-000000000112', session_revision: 'a'.repeat(64), task_id: `task-r${n}`, device_id: `dev-r${n}`, config_index: 0 },
      category: 'switching', operation_id: 'create_vlan', hostname: `R${n}`, vendor: 'cisco', platform: 'ios', captured_at: '2026-10-09T00:00:00Z',
      content_sha256: 'c'.repeat(64), content_encoding: 'utf-8', authority: {}, validity: 'historical_not_checked', configuration: '! immutable original\n', record_sha256: 'd'.repeat(64) } };
}
export async function fixture(page: Page, content = initial) {
  const records: Record<string, WorkingDocument> = { [idFor(1)]: record(1, content), [idFor(2)]: record(2) };
  const mutations: string[] = [];
  page.on('request', (request) => { if (request.method() !== 'GET' && request.url().includes('/api/')) mutations.push(request.method() + ' ' + request.url()); });
  await page.route(workingUrl, (route) => {
    expect(route.request().method()).toBe('GET');
    return route.fulfill({ json: { api_version: 1, documents: Object.values(records), limit: 128 } });
  });
  await page.route(workingUrl + '/*', (route) => {
    const id = route.request().url().split('/').at(-1)!;
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON(); expect(body.expected_revision).toBe(records[id].revision);
      records[id] = { ...records[id], content: body.content, revision: crypto.randomUUID(), save_sequence: records[id].save_sequence + 1 };
    }
    return route.fulfill({ json: records[id] });
  });
  await page.route('**/api/v1/workbench/artifacts/generated-originals', (route) => route.fulfill({ json: { api_version: 1, artifacts: Object.values(records).map((x) => x.original), limit: 128 } }));
  await page.route('**/api/v1/workbench/artifacts/generated-originals/*', (route) => route.fulfill({ json: Object.values(records).find((x) => route.request().url().endsWith(x.original.artifact_id))!.original }));
  await page.goto('/'); await open(page);
  return { records, mutations };
}
export async function open(page: Page, n = 1) {
  await page.getByRole('button', { name: new RegExp(`^Open working file R${n} `) }).click();
  await expect.poll(() => page.evaluate(() => window.__reviewTest.editors().filter((x) => x.uri?.startsWith('inmemory://v9-working/')).map((x) => x.uri))).toEqual([`inmemory://v9-working/${idFor(n)}/configuration`]);
}
export const snapshot = (page: Page) => page.evaluate(() => window.__reviewTest.snapshot());
export const buffer = (page: Page) => page.evaluate(() => window.__reviewTest.editors().find((x) => x.uri?.startsWith('inmemory://v9-working/'))!.text);
export async function proposal(page: Page, proposedContent: string, overrides: Partial<ChangeProposal> = {}): Promise<ChangeProposal> {
  const base = await page.evaluate(() => window.__reviewTest.base());
  return { ...base!, proposalId: crypto.randomUUID(), proposedContent, source: 'Controlled test producer (not AI)', ...overrides };
}
export const stage = (page: Page, value: ChangeProposal) => page.evaluate((input) => window.__reviewTest.stage(input), value);
export async function edit(page: Page, text: string) {
  await page.locator('.working-buffer-host .view-lines').click();
  await page.keyboard.press('Control+A'); await page.keyboard.insertText(text);
  await expect.poll(() => buffer(page)).toBe(text);
}
export async function reviewReady(page: Page) {
  await expect(page.getByLabel('Inline change review').locator('.monaco-diff-editor')).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__reviewTest.diffs()[0]?.changes)).not.toBeNull();
}

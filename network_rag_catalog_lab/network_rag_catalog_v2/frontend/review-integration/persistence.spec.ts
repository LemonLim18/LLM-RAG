import { expect, test } from '@playwright/test';
import { spawn, type ChildProcess } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, readFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, resolve, join, sep } from 'node:path';
import { buffer, proposal, reviewReady, stage } from '../review-tests/helpers';

test('real working file → test-only proposal → accept → Ctrl+S → new backend/browser; original stays unchanged', async ({ browser, request }, info) => {
  const root = await mkdtemp(join(tmpdir(), 'v9-working-browser-review-'));
  const repo = resolve('..'); const python = resolve(repo, '../../.venv/Scripts/python.exe');
  const api = 'http://127.0.0.1:8000/api/v1'; const sessionId = '00000000-0000-4000-8000-000000000112';
  let child: ChildProcess | undefined; let log = '';
  const stop = async () => { if (child && child.exitCode === null) { const exited = once(child, 'exit'); child.kill(); await exited; } };
  const start = async () => {
    child = spawn(python, ['-m', 'tests.workbench_working_server', root], { cwd: repo, windowsHide: true, stdio: 'pipe' });
    child.stdout?.on('data', (data) => { log += data; }); child.stderr?.on('data', (data) => { log += data; });
    await expect.poll(async () => {
      if (child?.exitCode !== null) throw new Error(log);
      try { return (await request.get(api + '/health')).status(); } catch { return 0; }
    }, { timeout: 20_000 }).toBe(200);
    return child.pid;
  };
  const context = await browser.newContext(); let next: Awaited<ReturnType<typeof browser.newContext>> | undefined;
  const mutations: string[] = [];
  const inventoryBefore = await readFile(join(repo, 'data/inventory/devices.json'));
  try {
    const pid = await start(); const sessionPath = join(root, `sessions/${sessionId}.json`);
    const sessionBefore = await readFile(sessionPath); const mtime = (await stat(sessionPath)).mtimeMs;
    const page = await context.newPage(); page.on('request', (r) => { if (r.method() !== 'GET' && r.url().includes('/api/')) mutations.push(r.method() + ' ' + r.url()); });
    await page.goto('/'); await page.getByRole('button', { name: 'Local V9', exact: true }).click();
    await page.getByLabel('Saved session ID', { exact: true }).fill(sessionId); await page.getByRole('button', { name: 'Restore saved session', exact: true }).click();
    await expect(page.getByLabel('Local V9 plan review')).toBeVisible(); expect(mutations).toEqual([]);
    const created = page.waitForResponse((r) => r.url().endsWith('/working-documents') && r.request().method() === 'POST');
    await page.getByLabel('Local V9 session result').getByRole('button', { name: 'Open in Editor · dev-r1 · output 1', exact: true }).click();
    const response = await created; expect(response.status()).toBe(201); const document = (await response.json()).document;
    const originalPath = join(root, 'workbench/generated_originals', document.original.artifact_id + '.json'); const originalBefore = await readFile(originalPath);
    await expect(page.getByLabel('Editable working document').locator('.view-lines')).toContainText('SALES');
    const proposed = 'vlan 100\n name REVIEWED-ENGINEERING\n';
    expect((await stage(page, await proposal(page, proposed))).status).toBe('staged'); await reviewReady(page);
    expect(await buffer(page)).toBe(document.content); expect(mutations).toHaveLength(2);
    await page.getByRole('button', { name: 'Accept Changes' }).click(); expect(await buffer(page)).toBe(proposed); expect(mutations).toHaveLength(2);
    const saved = page.waitForResponse((r) => r.request().method() === 'PUT'); await page.keyboard.press('Control+s');
    const saveResponse = await saved; expect(saveResponse.status()).toBe(200); const updated = await saveResponse.json();
    expect(updated.revision).not.toBe(document.revision); expect(updated.content).toBe(proposed);
    await expect(page.getByText('Saved working content · UNVALIDATED · not deployed')).toBeVisible();
    await context.close(); await stop(); expect(await start()).not.toBe(pid);
    next = await browser.newContext(); const reopened = await next.newPage();
    reopened.on('request', (r) => { if (r.method() !== 'GET' && r.url().includes('/api/')) mutations.push(r.method() + ' ' + r.url()); });
    await reopened.goto('/'); await reopened.getByRole('button', { name: /^Open working file R1 / }).click();
    await expect(reopened.getByLabel('Editable working document').locator('.view-lines')).toContainText('REVIEWED-ENGINEERING');
    expect(await (await request.get(api + '/workbench/working-documents/' + document.document_id)).json()).toEqual(updated);
    await expect(reopened.getByLabel('Pending change proposal')).toHaveCount(0);
    await reopened.getByRole('button', { name: /^Open saved original R1 / }).click();
    await expect(reopened.getByLabel('Saved original document').locator('.view-lines')).toContainText('SALES');
    expect(await readFile(originalPath)).toEqual(originalBefore); expect(await readFile(sessionPath)).toEqual(sessionBefore);
    expect((await stat(sessionPath)).mtimeMs).toBe(mtime); expect(await readFile(join(repo, 'data/inventory/devices.json'))).toEqual(inventoryBefore);
    expect(mutations.map((x) => x.split(' ')[0])).toEqual(['POST', 'POST', 'PUT']);
    await reopened.getByRole('button', { name: /^Open working file R1 / }).click();
    await reopened.screenshot({ path: info.outputPath('restarted-reviewed-working-file.png') });
  } finally {
    await context.close(); await next?.close(); await stop();
    await info.attach('isolated-backend-log', { body: log, contentType: 'text/plain' });
    // Delete only the validated, exact mkdtemp directory owned by this test.
    expect(resolve(root).startsWith(resolve(tmpdir()) + sep) && basename(root).startsWith('v9-working-browser-review-'), 'Safe test cleanup path').toBe(true);
    await rm(root, { recursive: true, force: true });
  }
});

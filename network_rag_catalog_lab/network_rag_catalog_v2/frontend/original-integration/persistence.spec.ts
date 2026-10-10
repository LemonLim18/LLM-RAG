import { expect, test } from '@playwright/test';
import { spawn, type ChildProcess } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, readFile, readdir, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';

test('unmocked browser captures, then reopens original after complete backend and browser-context restart', async ({ browser, request }, testInfo) => {
  const root = await mkdtemp(join(tmpdir(), 'v9-original-browser-'));
  const repo = resolve('..');
  const python = resolve(repo, '../../.venv/Scripts/python.exe');
  const api = 'http://127.0.0.1:8000/api/v1';
  const sessionId = '00000000-0000-4000-8000-000000000111';
  const artifactDirectory = join(root, 'workbench/generated_originals');
  const inventoryBefore = await readFile(join(repo, 'data/inventory/devices.json'));
  let child: ChildProcess | undefined;
  let log = '';
  const stop = async () => {
    if (!child || child.exitCode !== null) return;
    const exited = once(child, 'exit'); child.kill(); await exited;
  };
  const start = async () => {
    child = spawn(python, ['-m', 'tests.workbench_original_server', root], { cwd: repo, windowsHide: true, stdio: 'pipe' });
    child.stdout?.on('data', (data) => { log += data.toString(); });
    child.stderr?.on('data', (data) => { log += data.toString(); });
    await expect.poll(async () => {
      if (child?.exitCode !== null) throw new Error(log);
      try { return (await request.get(api + '/health')).status(); } catch { return 0; }
    }, { timeout: 20_000 }).toBe(200);
    return child.pid;
  };
  const mutations: string[] = [];
  const context = await browser.newContext();
  let secondContext: Awaited<ReturnType<typeof browser.newContext>> | undefined;
  try {
    const initialPid = await start();
    const sessionPath = join(root, `sessions/${sessionId}.json`);
    const sessionBefore = await readFile(sessionPath);
    const sessionTime = (await stat(sessionPath)).mtimeMs;
    const page = await context.newPage();
    page.on('request', (r) => { if (r.method() !== 'GET' && r.url().includes('/api/')) mutations.push(r.url()); });
    await page.goto('http://127.0.0.1:5173');
    await page.getByRole('button', { name: 'Local V9', exact: true }).click();
    await page.getByLabel('Saved session ID', { exact: true }).fill(sessionId);
    await page.getByRole('button', { name: 'Restore saved session', exact: true }).click();
    await page.getByRole('button', { name: 'Open read-only in Monaco · output 1', exact: true }).click();
    await expect(page.getByText('Saved historical state · current validity not checked', { exact: true }).last()).toBeVisible();
    const captured = page.waitForResponse((response) => response.url().endsWith('/generated-originals') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Save to Workspace' }).click();
    const capture = await captured; expect(capture.status()).toBe(201);
    const record = (await capture.json()).artifact;
    const row = page.getByRole('button', { name: /^Open saved original R1 / });
    await row.click(); await expect(page.getByLabel('Saved original document').locator('.view-lines')).toContainText('persisted integration original');
    const persisted = await readFile(join(artifactDirectory, record.artifact_id + '.json'));
    expect(JSON.parse(persisted.toString()).configuration).toBe('! persisted integration original\r\nrouter ospf 10\r\n  ! exact whitespace  \r\n');
    await context.close(); await stop();
    const newPid = await start(); expect(newPid).not.toBe(initialPid);
    secondContext = await browser.newContext();
    const reopened = await secondContext.newPage();
    reopened.on('request', (r) => { if (r.method() !== 'GET' && r.url().includes('/api/')) mutations.push(r.url()); });
    await reopened.goto('http://127.0.0.1:5173');
    await reopened.getByRole('button', { name: /^Open saved original R1 / }).click();
    await expect(reopened.getByLabel('Saved original document').locator('.monaco-editor')).toBeVisible();
    await expect(reopened.getByLabel('Saved original document').locator('.view-lines')).toContainText('persisted integration original');
    await reopened.getByLabel('Saved original document').locator('.view-lines').click(); await reopened.keyboard.type('BLOCKED');
    await expect(reopened.getByLabel('Saved original document').locator('.view-lines')).not.toContainText('BLOCKED');
    const detail = await request.get(api + '/workbench/artifacts/generated-originals/' + record.artifact_id);
    expect(await detail.json()).toEqual(record);
    expect(await readFile(join(artifactDirectory, record.artifact_id + '.json'))).toEqual(persisted);
    expect(await readdir(artifactDirectory)).toEqual([record.artifact_id + '.json']);
    expect(await readFile(sessionPath)).toEqual(sessionBefore); expect((await stat(sessionPath)).mtimeMs).toBe(sessionTime);
    expect(await readFile(join(repo, 'data/inventory/devices.json'))).toEqual(inventoryBefore);
    expect(mutations).toHaveLength(1); expect(mutations[0]).toContain('/generated-originals');
    await reopened.screenshot({ path: testInfo.outputPath('restarted-original.png') });
  } finally {
    await context.close(); await secondContext?.close(); await stop();
    await testInfo.attach('isolated-backend-log', { body: log, contentType: 'text/plain' });
    // Only the exact mkdtemp directory owned by this test is removed.
    await rm(root, { recursive: true, force: true });
  }
});

import { expect, test } from '@playwright/test';
import { buffer, edit, fixture, idFor, initial, open, proposal, reviewReady, snapshot, stage, workingUrl } from './helpers';

for (const [name, before, after] of [
  ['insertion', initial, initial + '! added\n'],
  ['deletion to empty', initial, ''],
  ['replacement', initial, 'vlan 200\n name ENGINEERING\n'],
  ['empty to Unicode', '', '! 東京 🌐\n'],
  ['CRLF preserved', 'vlan 100\r\n name SALES\r\n', 'vlan 200\r\n name DATA\r\n'],
  ['uniform EOL change', initial, 'vlan 200\r\n name DATA\r\n'],
  ['BOM preserved', '\uFEFFvlan 100\n', '\uFEFFvlan 200\n'],
]) test(`${name}: native inline preview, buffer isolation, whole accept and undo`, async ({ page }) => {
  const f = await fixture(page, before); const base = await snapshot(page);
  expect((await stage(page, await proposal(page, after))).status).toBe('staged'); await reviewReady(page);
  expect(await buffer(page)).toBe(before); expect((await snapshot(page)).tabs[idFor()].content).toBe(before);
  await expect(page.getByRole('button', { name: 'Save (Ctrl+S)' })).toBeDisabled(); await page.keyboard.press('Control+s');
  await page.getByLabel('Inline change review').locator('.editor.modified .view-lines:not([monaco-view-zone])').click();
  await page.keyboard.type('NO-WRITE'); expect(await buffer(page)).toBe(before);
  expect((await page.evaluate(() => window.__reviewTest.diffs()))[0].proposed).toBe(after);
  await page.getByRole('button', { name: 'Accept Changes', exact: true }).click();
  await expect(page.getByLabel('Inline change review')).toHaveCount(0); expect(await buffer(page)).toBe(after);
  const accepted = (await snapshot(page)).tabs[idFor()];
  expect(accepted.content).toBe(after); expect(accepted.saved).toEqual(base.tabs[idFor()].saved);
  expect(accepted.bufferEpoch).toBeGreaterThan(base.tabs[idFor()].bufferEpoch);
  await expect(page.getByText('Unsaved changes · UNVALIDATED · not deployed')).toBeVisible(); expect(f.mutations).toEqual([]);
  await page.keyboard.press('Control+z'); await expect.poll(() => buffer(page)).toBe(before);
  await page.keyboard.press('Control+y'); await expect.poll(() => buffer(page)).toBe(after);
  expect(f.records[idFor()].original.configuration).toBe('! immutable original\n');
});

test('separated change regions use Monaco single-pane diff, reject keeps manual edits and undo', async ({ page }, info) => {
  const many = Array.from({ length: 18 }, (_, i) => `! line ${i}`).join('\n'); const f = await fixture(page, many);
  await page.evaluate((text) => window.__reviewTest.modelEdit(text), many + '\n! MANUAL'); const before = await snapshot(page);
  const changed = (many + '\n! MANUAL').replace('! line 1\n', '! changed 1\n').replace('! line 14\n', '! changed 14\n');
  expect((await stage(page, await proposal(page, changed))).status).toBe('staged'); await reviewReady(page);
  await expect.poll(() => page.evaluate(() => window.__reviewTest.diffs()[0]?.changes?.length)).toBe(2);
  const layout = (await page.evaluate(() => window.__reviewTest.diffs()))[0].originalLayout;
  expect(layout.width).toBe(Math.max(5, layout.decorationsLeft)); // Original line-number gutter only, not a second text pane.
  expect((await page.getByLabel('Inline change review').locator('.editor.modified').boundingBox())!.width).toBeGreaterThan(200);
  await expect(page.getByLabel('Inline change review').locator('.line-insert').first()).toBeVisible();
  await expect(page.getByLabel('Inline change review').locator('.line-delete').first()).toBeVisible();
  await page.screenshot({ path: info.outputPath('native-inline-review.png') });
  await page.getByRole('button', { name: 'Reject Changes' }).click();
  expect((await snapshot(page)).tabs[idFor()].content).toBe(before.tabs[idFor()].content);
  expect((await snapshot(page)).tabs[idFor()].bufferEpoch).toBe(before.tabs[idFor()].bufferEpoch);
  await page.keyboard.press('Control+z'); await expect.poll(() => buffer(page)).toBe(many); expect(f.mutations).toEqual([]);
});

test('manual Review Changes uses saved working baseline, closes without save, and supports no changes', async ({ page }) => {
  const f = await fixture(page); await edit(page, '! accepted manually');
  await page.getByRole('button', { name: 'Review Changes', exact: true }).click(); await reviewReady(page);
  expect((await page.evaluate(() => window.__reviewTest.diffs()))[0]).toMatchObject({ base: initial, proposed: '! accepted manually' });
  await expect(page.getByRole('button', { name: 'Accept Changes' })).toHaveCount(0);
  await page.keyboard.press('Control+s'); expect(f.mutations).toEqual([]);
  await page.getByRole('button', { name: 'Close Review', exact: true }).click(); expect(await buffer(page)).toBe('! accepted manually');
  await page.keyboard.press('Control+s'); await expect(page.getByText('Saved working content · UNVALIDATED · not deployed')).toBeVisible();
  await edit(page, '! later'); await page.getByRole('button', { name: 'Review Changes', exact: true }).click(); await reviewReady(page);
  expect((await page.evaluate(() => window.__reviewTest.diffs()))[0].base).toBe('! accepted manually');
  await page.getByRole('button', { name: 'Close Review', exact: true }).click(); await edit(page, '! accepted manually');
  await page.getByRole('button', { name: 'Review Changes', exact: true }).click();
  await expect(page.getByLabel('Inline change review').getByRole('status')).toContainText('No changes'); expect(f.mutations).toHaveLength(1);
});

test('no-op and invalid proposals cannot change content or stage review', async ({ page }) => {
  const f = await fixture(page);
  expect((await stage(page, await proposal(page, initial))).status).toBe('no_change');
  await expect(page.getByText('No changes proposed. The working buffer is unchanged.')).toBeVisible();
  for (const overrides of [{ proposalId: '' }, { baseBufferEpoch: -1 }, { proposedContent: 'x'.repeat(1024 * 1024 + 1) }]) {
    expect((await stage(page, await proposal(page, '! change', overrides))).status).toBe('refused');
  }
  await expect(page.getByLabel('Inline change review')).toHaveCount(0); expect(await buffer(page)).toBe(initial); expect(f.mutations).toEqual([]);
});

test('second proposal and wrong acceptance identity cannot replace the pending one', async ({ page }) => {
  await fixture(page); const first = await proposal(page, '! first'); await stage(page, first);
  expect((await stage(page, await proposal(page, '! second'))).status).toBe('refused');
  expect((await page.evaluate(({ id }) => window.__reviewTest.accept(id, 'wrong-id'), { id: idFor() })).status).toBe('refused');
  expect((await snapshot(page)).tabs[idFor()].proposal?.proposalId).toBe(first.proposalId); expect(await buffer(page)).toBe(initial);
  await page.getByRole('button', { name: 'Accept Changes' }).click(); expect(await buffer(page)).toBe('! first');
  expect((await stage(page, first)).status).toBe('refused');
});

test('wrong, inactive and late-navigation document proposals never steal the editor', async ({ page }) => {
  await fixture(page); const late = await proposal(page, '! late'); await open(page, 2);
  expect((await stage(page, late)).status).toBe('refused'); expect((await snapshot(page)).activeId).toBe(idFor(2));
  expect((await stage(page, await proposal(page, '! wrong', { documentId: 'working-missing' }))).status).toBe('refused');
  await open(page, 1); await page.getByRole('tab', { name: 'Samples', exact: true }).click();
  expect((await stage(page, late)).status).toBe('refused');
  await expect(page.getByRole('tab', { name: 'Samples', exact: true })).toHaveAttribute('aria-selected', 'true');
  await open(page, 1); expect(await buffer(page)).toBe(initial);
});

test('ABA buffer edits and saved-revision changes reject stale asynchronous proposals', async ({ page }) => {
  await fixture(page); const old = await proposal(page, '! stale');
  await edit(page, '! interim'); await edit(page, initial); expect(await buffer(page)).toBe(old.baseContent);
  expect((await stage(page, old)).status).toBe('refused');
  const beforeSave = await proposal(page, '! stale revision'); await page.keyboard.press('Control+s');
  await expect.poll(async () => (await snapshot(page)).tabs[idFor()].saved.revision).not.toBe(beforeSave.baseRevision);
  expect((await stage(page, beforeSave)).status).toBe('refused');
  expect((await stage(page, await proposal(page, '! wrong text', { baseContent: 'not the current text' }))).status).toBe('refused');
});

test('pending proposal becomes stale after actual external model edit, even A to B to A; reject preserves latest text', async ({ page }) => {
  const f = await fixture(page); const value = await proposal(page, '! suggested'); await stage(page, value); await reviewReady(page);
  await page.evaluate(() => { window.__reviewTest.modelEdit('! external'); window.__reviewTest.modelEdit('vlan 100\n name SALES\n'); });
  await expect(page.getByRole('button', { name: 'Accept Changes' })).toBeDisabled();
  expect((await page.evaluate(({ id, proposalId }) => window.__reviewTest.accept(id, proposalId), { id: idFor(), proposalId: value.proposalId })).status).toBe('refused');
  await expect(page.getByLabel('Pending change proposal')).toContainText('Stale proposal');
  await page.getByRole('button', { name: 'Reject Changes' }).click(); expect(await buffer(page)).toBe(initial); expect(f.mutations).toEqual([]);
});

test('pending save and uncertain save block proposals; confirmed late save cannot adopt old base', async ({ page }) => {
  const f = await fixture(page); await edit(page, '! save me'); const value = await proposal(page, '! later');
  let release!: () => void; const wait = new Promise<void>((resolve) => { release = resolve; });
  await page.route(workingUrl + '/*', async (route) => { if (route.request().method() !== 'PUT') return route.fallback(); await wait; return route.fallback(); });
  await page.keyboard.press('Control+s'); await expect(page.getByRole('button', { name: 'Saving…' })).toBeDisabled();
  expect((await stage(page, value)).status).toBe('refused'); release();
  await expect(page.getByRole('button', { name: 'Save (Ctrl+S)' })).toBeEnabled(); expect((await stage(page, value)).status).toBe('refused');
  await page.route(workingUrl + '/*', (route) => route.request().method() === 'PUT' ? route.abort('connectionreset') : route.fallback());
  await page.keyboard.press('Control+s'); await expect(page.getByLabel('Editable working document').getByRole('alert')).toContainText('OUTCOME_UNCERTAIN');
  expect((await stage(page, await proposal(page, '! blocked'))).status).toBe('refused'); expect(f.mutations).toHaveLength(2);
});

test('mixed line endings cannot be silently normalized on acceptance', async ({ page }) => {
  await fixture(page); await stage(page, await proposal(page, 'vlan 200\r\n name DATA\n')); await reviewReady(page);
  await page.getByRole('button', { name: 'Accept Changes' }).click();
  await expect(page.getByText(/Monaco cannot apply this text exactly/)).toBeVisible(); expect(await buffer(page)).toBe(initial);
  await expect(page.getByLabel('Pending change proposal')).toBeVisible();
  await page.getByRole('button', { name: 'Reject Changes' }).click(); expect(await buffer(page)).toBe(initial);
});

test('rapid view switches retain proposal, sample edits and originals; review models are cleaned up', async ({ page }) => {
  const f = await fixture(page); await page.getByRole('tab', { name: 'Samples', exact: true }).click();
  await page.locator('.view-lines').click(); await page.keyboard.press('Control+End'); await page.keyboard.insertText('\n! SAMPLE-KEEP');
  await open(page); await edit(page, '! unsaved'); await stage(page, await proposal(page, '! accepted later')); await reviewReady(page);
  await open(page, 2); expect(await buffer(page)).toBe(initial);
  await expect.poll(() => page.evaluate(() => window.__reviewTest.models().filter((uri) => uri.startsWith('inmemory://v9-review/')).length)).toBe(0);
  await open(page); await reviewReady(page); expect((await snapshot(page)).tabs[idFor()].content).toBe('! unsaved');
  await page.getByRole('button', { name: 'Reject Changes' }).click();
  for (let i = 0; i < 3; i++) { await page.getByRole('button', { name: 'Review Changes', exact: true }).click(); await reviewReady(page); await page.getByRole('button', { name: 'Close Review', exact: true }).click(); }
  expect(await page.evaluate(() => window.__reviewTest.models().filter((uri) => uri.startsWith('inmemory://v9-review/')))).toEqual([]);
  await page.getByRole('button', { name: /^Open saved original R1 / }).click();
  await expect(page.getByLabel('Saved original document').locator('.view-lines')).toContainText('immutable original');
  await page.getByRole('tab', { name: 'Samples', exact: true }).click(); await expect(page.locator('.view-lines')).toContainText('SAMPLE-KEEP');
  await open(page); expect(await buffer(page)).toBe('! unsaved');
  await page.getByRole('button', { name: 'Demo mock', exact: true }).click(); await page.getByLabel('Message the demo Copilot').fill('independent');
  await page.getByRole('button', { name: 'Send demo message' }).click(); await expect(page.getByText('Mock response: I received “independent”')).toBeVisible();
  await page.getByRole('button', { name: 'Add Device', exact: true }).click(); await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Close registration', exact: true }).click(); expect(await buffer(page)).toBe('! unsaved'); expect(f.mutations).toEqual([]);
});

test('accepted changes save only on Ctrl+S and reopen through existing persistence', async ({ page }) => {
  const f = await fixture(page); await stage(page, await proposal(page, '! accepted then saved')); await reviewReady(page);
  await page.getByRole('button', { name: 'Accept Changes' }).click(); expect(f.mutations).toEqual([]);
  await page.keyboard.press('Control+s'); await expect(page.getByText('Saved working content · UNVALIDATED · not deployed')).toBeVisible();
  expect(f.mutations).toHaveLength(1); expect(f.records[idFor()].content).toBe('! accepted then saved');
  await page.reload(); await open(page); expect(await buffer(page)).toBe('! accepted then saved');
  expect((await snapshot(page)).tabs[idFor()].proposal).toBeUndefined();
});

test('review retains the real working editor identity and cursor on reject and accept', async ({ page }) => {
  await fixture(page); await page.locator('.working-buffer-host .view-lines').click();
  await page.keyboard.press('Control+Home'); await page.keyboard.press('ArrowDown'); await page.keyboard.press('ArrowRight');
  const current = () => page.evaluate(() => window.__reviewTest.editors().find((item) => item.uri?.startsWith('inmemory://v9-working/'))!);
  const before = await current(); await stage(page, await proposal(page, 'vlan 100\n name DATA\n')); await reviewReady(page);
  expect((await current()).id).toBe(before.id); expect((await current()).readOnly).toBe(true);
  await page.getByRole('button', { name: 'Reject Changes' }).click();
  expect(await current()).toMatchObject({ id: before.id, position: before.position, readOnly: false });
  await stage(page, await proposal(page, 'vlan 100\n name DATA\n')); await reviewReady(page);
  await page.getByRole('button', { name: 'Accept Changes' }).click();
  expect(await current()).toMatchObject({ id: before.id, position: before.position, readOnly: false });
  await expect.poll(() => page.evaluate(() => window.__reviewTest.models().filter((uri) => uri.startsWith('inmemory://v9-review/')).length)).toBe(0);
});

test('a transient pending proposal is never saved or restored by browser reload', async ({ page }) => {
  const f = await fixture(page); await stage(page, await proposal(page, '! never accepted')); await reviewReady(page);
  await page.reload(); await open(page); expect(await buffer(page)).toBe(initial);
  expect((await snapshot(page)).tabs[idFor()].proposal).toBeUndefined();
  await expect(page.getByLabel('Pending change proposal')).toHaveCount(0); expect(f.mutations).toEqual([]);
});

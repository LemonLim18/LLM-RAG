const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const compiled = ts.transpileModule(fs.readFileSync(__dirname + '/../components/ansible/workspaceCreation.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;
const scope = { exports: {} };
vm.runInNewContext(compiled, scope);
const { creationDirectory, creationBranch } = scope.exports;
const tree = [{ path: 'project', type: 'dir', children: [
  { path: 'playbooks', type: 'dir', children: [
    { path: 'playbooks/release.v1', type: 'dir', children: [{ path: 'playbooks/release.v1/README', type: 'file' }] },
  ] },
  { path: 'roles', type: 'dir' },
] }];
const allowed = path => path === 'playbooks' || path.startsWith('playbooks/');
test('unsaved draft with missing parents resolves to a listed writable ancestor', () => {
  assert.equal(creationDirectory(tree, 'playbooks/drafts/missing/new.cfg', allowed), 'playbooks');
});
test('uses node type rather than filename extension to identify directories', () => {
  assert.equal(creationDirectory(tree, 'playbooks/release.v1/README', allowed), 'playbooks/release.v1');
  assert.equal(creationDirectory(tree, 'playbooks/release.v1', allowed), 'playbooks/release.v1');
});
test('protected and virtual selections fall back; an absent workspace fails closed', () => {
  for (const selected of ['reference/file.j2', 'generated/job_1/file.cfg', 'roles/main.yml', null]) {
    assert.equal(creationDirectory(tree, selected, allowed), 'playbooks');
  }
  assert.equal(creationDirectory([], 'playbooks/draft.cfg', allowed), null);
});
test('creation expands virtual groups whose paths are not filesystem prefixes', () => {
  assert.equal(creationBranch(tree[0], 'playbooks/release.v1'), true);
  assert.equal(creationBranch(tree[0].children[1], 'playbooks/release.v1'), false);
  assert.equal(creationBranch(tree[0], null), false);
});

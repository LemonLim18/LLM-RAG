const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const scope = {exports: {}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(__dirname + '/../src/utils/assistantCode.ts', 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS},
}).outputText, scope);
const {chatLanguage, tokenClass, tokenSegments, copyMarkdown} = scope.exports;

test('chat fences reuse supported languages, with safe unknown fallback', () => {
  for (const [fence, code, expected] of [['ansible', '- hosts: all', 'yaml'], ['j2', '{{ name }}', 'jinja2'],
    ['yaml', 'name: {{ name }}', 'jinja2'], ['python', 'print(1)', 'python'], ['json', '{}', 'json'],
    ['bash', 'echo hi', 'shell'], ['ios', 'router bgp 65000', 'network-config'],
    ['diff', '+description New', 'diff'], ['patch', '-description Old', 'diff'],
    ['text', 'neighbor 192.0.2.2 remote-as 65001', 'network-config'], ['untrusted-language', '<script>', 'plaintext']]) {
    assert.equal(chatLanguage(fence, code), expected);
  }
});
test('static spans preserve source and restrict CSS classes', () => {
  const text = '  neighbor 192.0.2.2 remote-as 65001';
  const segments = tokenSegments(text, [{offset: 0, type: ''}, {offset: 2, type: 'keyword'}, {offset: 10, type: 'number'}]);
  assert.equal(segments.map(s => s.text).join(''), text);
  assert.equal(tokenClass('keyword.jinja2'), 'syntax-keyword');
  assert.equal(tokenClass('" onclick="evil'), '');
});
test('whole response copy retains exact Markdown; clipboard denial reports failure', async () => {
  const markdown = '**OSPF**\n\n```ios\n router-id 192.0.2.1\n```\n\n|AS|Peer|\n|-|-|\n|65000|192.0.2.2|';
  let copied;
  assert.equal(await copyMarkdown(markdown, async value => {copied = value;}), 'copied');
  assert.equal(copied, markdown);
  assert.equal(await copyMarkdown(markdown, async () => {throw new Error('Permission denied');}), 'failed');
});
test('copy preserves Unicode, CRLF, nested fences, empty replies and source text exactly', async () => {
  for (const source of ['', '**已记录 · R2 → R1**\r\n\r\n```jinja2\r\n{{ name | default("上联") }}\r\n```',
    '````md\n```yaml\n- hosts: reviewed\n```\n````\n\nSources: design.pdf, page 4',
    '| Device | Address |\n|---|---|\n| R2 | 192.0.2.2 |\n']) {
    let actual;
    assert.equal(await copyMarkdown(source, async value => { actual = value; }), 'copied');
    assert.equal(actual, source);
  }
});

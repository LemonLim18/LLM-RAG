/** Static chat tokenization only: no editor instance or command execution. */
export function chatLanguage(fence: string, source: string): string {
  const name = fence.toLowerCase().trim();
  const aliases: Record<string, string> = {yaml: 'yaml', yml: 'yaml', ansible: 'yaml',
    j2: 'jinja2', jinja: 'jinja2', jinja2: 'jinja2', python: 'python', py: 'python',
    json: 'json', diff: 'diff', patch: 'diff', sh: 'shell', bash: 'shell', shell: 'shell',
    ios: 'network-config', iosxe: 'network-config', cisco: 'network-config',
    junos: 'network-config', vrp: 'network-config', cli: 'network-config',
    cfg: 'network-config', 'network-config': 'network-config',
    javascript: 'javascript', js: 'javascript', typescript: 'typescript', ts: 'typescript'};
  if (aliases[name]) return /\{[{%#]/.test(source) && ['yaml', 'yml', 'ansible', 'cfg', 'cli'].includes(name) ? 'jinja2' : aliases[name];
  if ((!name || name === 'text' || name === 'plaintext') && /\{[{%#]/.test(source)) return 'jinja2';
  if ((!name || name === 'text' || name === 'plaintext') && /^(?:\s*(?:router (?:ospf|bgp)|router-id |neighbor |network .* area |interface |ip route |set (?:interfaces|protocols|routing-options) |ospf \d|bgp \d))/m.test(source)) return 'network-config';
  return 'plaintext';
}

export function tokenClass(type: string): string {
  const root = type.split('.')[0];
  return ['comment', 'keyword', 'string', 'number', 'variable', 'predefined', 'operator', 'delimiter', 'inserted', 'deleted'].includes(root) ? 'syntax-' + root : '';
}

export function tokenSegments(line: string, tokens: {offset: number; type: string}[]) {
  if (!tokens.length) return [{text: line, className: ''}];
  return tokens.map((token, index) => ({text: line.slice(token.offset, tokens[index + 1]?.offset ?? line.length), className: tokenClass(token.type)}));
}

export async function copyMarkdown(content: string, write: (text: string) => Promise<void>): Promise<'copied' | 'failed'> {
  try { await write(content); return 'copied'; } catch { return 'failed'; }
}

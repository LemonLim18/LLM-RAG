import type { AnsibleFileNode } from '../../typesLLM';

export function creationBranch(node: AnsibleFileNode, target: string | null): boolean {
  return !!target && (node.path === target || !!node.children?.some(child => creationBranch(child, target)));
}

/** Resolve against the workspace listing, never an unsaved tab's inferred directory. */
export function creationDirectory(
  tree: AnsibleFileNode[], selected: string | null, allowed: (path: string) => boolean,
): string | null {
  const nodes = new Map<string, AnsibleFileNode>();
  const visit = (items: AnsibleFileNode[]) => items.forEach(node => {
    nodes.set(node.path, node);
    if (node.children) visit(node.children);
  });
  visit(tree);
  const valid = (path: string) => nodes.get(path)?.type === 'dir' && allowed(path);
  let candidate = selected || '';
  while (candidate) {
    if (valid(candidate)) return candidate;
    const slash = candidate.lastIndexOf('/');
    candidate = slash < 0 ? '' : candidate.slice(0, slash);
  }
  return valid('playbooks') ? 'playbooks' : null;
}

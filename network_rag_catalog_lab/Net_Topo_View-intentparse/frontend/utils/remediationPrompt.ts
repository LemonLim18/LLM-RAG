import type { ComplianceResultRecord } from '../src/services/api';
import type { ViewId } from '../types';

const MAX_LINES = 12;
const MAX_LINE_LEN = 120;

export const ANSIBLE_REMEDIATION_INTENT_KEY = 'ansible.remediationIntent';

export interface RemediationIntentPayload {
  intent_description: string;
  target_hosts: string[];
  vendor?: string;
  feature?: string;
}

function truncateLines(lines: string[], max = MAX_LINES): string[] {
  return lines.slice(0, max).map((l) => (l.length > MAX_LINE_LEN ? `${l.slice(0, MAX_LINE_LEN)}…` : l));
}

/** Build a natural-language seed for Ansible AI from a compliance / drift result. */
export function buildRemediationIntentPayload(
  event: ComplianceResultRecord,
  meta?: { vendor?: string | null; role?: string | null; hostname?: string | null },
): RemediationIntentPayload {
  const host = meta?.hostname || (event as { hostname?: string }).hostname || (event.device_id != null ? `device_id_${event.device_id}` : 'unknown');
  const target_hosts = meta?.hostname || (event as { hostname?: string }).hostname ? [String(meta?.hostname || (event as { hostname?: string }).hostname)] : [];
  const parts: string[] = [`Remediate configuration drift on ${host} (compliance status: ${event.status || 'unknown'}).`];
  if (meta?.role) parts.push(`Device role (inventory): ${meta.role}.`);
  if (meta?.vendor) parts.push(`Vendor/platform hint: ${meta.vendor}.`);
  const miss = event.missing_lines || [];
  const ext = event.extra_lines || [];
  const ch = event.changed_lines || [];
  if (miss.length) parts.push(`Baseline expects these lines to be present (add or restore):\n${truncateLines(miss).map((l) => `+ ${l}`).join('\n')}`);
  if (ext.length) parts.push(`These lines should be removed or aligned with policy/baseline:\n${truncateLines(ext).map((l) => `- ${l}`).join('\n')}`);
  if (ch.length) parts.push(`Changed stanzas:\n${ch.slice(0, MAX_LINES).map((c) => `Change from "${c.baseline}" to "${c.actual}"`).join('\n')}`);
  if (event.violated_policies?.length) parts.push(`Policy violations: ${event.violated_policies.map((v: { policy_id?: string; message?: string }) => `${v.policy_id || 'policy'}: ${v.message || ''}`).join('; ')}`);
  if (event.reason) parts.push(`Analysis: ${event.reason.slice(0, 500)}${event.reason.length > 500 ? '…' : ''}`);
  parts.push('Generate an Ansible playbook that applies the minimal safe changes to align this device with baseline and policy. Use the planned inventory hostnames.');
  const vendorRaw = (meta?.vendor || '').toLowerCase();
  const vendor = vendorRaw.includes('huawei') || vendorRaw.includes('vrp') ? 'huawei_vrp' : vendorRaw.includes('juniper') || vendorRaw.includes('junos') ? 'juniper_junos' : vendorRaw.includes('cisco') || vendorRaw.includes('ios') ? 'cisco_ios' : undefined;
  return { intent_description: parts.join('\n\n'), target_hosts, vendor, feature: 'interface' };
}

export function storeRemediationIntentAndGoStudio(payload: RemediationIntentPayload, setView: (v: ViewId) => void): void {
  try { sessionStorage.setItem(ANSIBLE_REMEDIATION_INTENT_KEY, JSON.stringify(payload)); } catch { /* quota */ }
  setView('ansible_studio');
}

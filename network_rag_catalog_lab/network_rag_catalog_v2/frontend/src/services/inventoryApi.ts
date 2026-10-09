import { apiBaseUrl, readApiJson } from './runtimeApi';

export interface InventoryNeighbor {
  device: string;
  interface: string;
}

export interface InventoryInterface {
  name: string;
  aliases: string[];
  type: string;
  enabled: boolean;
  role: string;
  neighbor: InventoryNeighbor | null;
}

export interface InventoryDevice {
  id: string;
  hostname: string;
  kind: string;
  display_name: string;
  aliases: string[];
  vendor: string;
  platform: string;
  version: string;
  site: string;
  role: string;
  location: string | null;
  status: string | null;
  tags: string[];
  interfaces: InventoryInterface[];
  capabilities: {
    features: string[];
    interface_name_style: string | null;
  };
}

export interface InventoryListResponse {
  api_version: 1;
  source: 'synthetic';
  inventory_revision: string;
  devices: InventoryDevice[];
}

export function readInventory(signal: AbortSignal): Promise<InventoryListResponse> {
  return readApiJson<InventoryListResponse>('/inventory/devices', signal);
}

export interface DeviceRegistration {
  expected_inventory_revision: string;
  device: Pick<InventoryDevice, 'hostname' | 'display_name' | 'kind' | 'vendor' | 'platform' | 'version' | 'site' | 'role' | 'location' | 'aliases' | 'tags'> & {
    capabilities: Pick<InventoryDevice['capabilities'], 'features'>;
    interfaces: Array<Omit<InventoryInterface, 'neighbor'>>;
  };
}
export interface InventoryDetailResponse {
  api_version: 1;
  source: 'synthetic';
  inventory_revision: string;
  device: InventoryDevice;
}
export class RegistrationError extends Error {
  constructor(public code: string, message: string) { super(message); }
}
export async function registerDevice(request: DeviceRegistration): Promise<InventoryDetailResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/inventory/devices`, {
      method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(request), signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new RegistrationError('OUTCOME_UNKNOWN', 'Connection lost. Registration may have saved. Reload inventory and inspect it before another submission.');
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const validation = Array.isArray(detail) ? detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.join('.')}: ${item.msg}`).join('; ') : null;
    throw new RegistrationError(detail?.code || 'INVALID_REGISTRATION', validation || detail?.message || 'Registration could not be confirmed. Reload inventory before trying again.');
  }
  if (body?.source !== 'synthetic' || !body.device?.id || body.device.hostname !== request.device.hostname.trim()
      || !/^[a-f0-9]{64}$/.test(body.inventory_revision)) {
    throw new RegistrationError('OUTCOME_UNKNOWN', 'Unexpected registration response. Reload inventory to inspect the saved outcome.');
  }
  return body as InventoryDetailResponse;
}

import { readApiJson } from './runtimeApi';

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

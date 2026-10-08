import type { ActivityEntry, ChatMessage, EditorDocument, Vendor } from '../app/types';

const sampleConfigurations: Record<string, string> = {
  'config-r1': `! DEMO CONFIGURATION — Cisco IOS-XE\n! In-memory sample; not generated or validated by V9\nhostname R1\n!\ninterface Loopback0\n description DEMO_ROUTER_ID\n ip address 10.255.0.1 255.255.255.255\n!\nrouter ospf 100\n router-id 10.255.0.1\n network 10.255.0.1 0.0.0.0 area 0\n!\nend\n`,
  'config-r2': `# DEMO CONFIGURATION — Huawei VRP\n# In-memory sample; not generated or validated by V9\nsysname R2\n#\ninterface LoopBack0\n description DEMO_ROUTER_ID\n ip address 10.255.0.2 255.255.255.255\n#\nospf 100 router-id 10.255.0.2\n area 0.0.0.0\n  network 10.255.0.2 0.0.0.0\n#\nreturn\n`,
  'config-r3': `## DEMO CONFIGURATION — Juniper Junos\n## In-memory sample; not generated or validated by V9\nsystem {\n    host-name R3;\n}\ninterfaces {\n    lo0 {\n        unit 0 {\n            family inet {\n                address 10.255.0.3/32;\n            }\n        }\n    }\n}\nrouting-options { router-id 10.255.0.3; }\n`,
  'config-sw1': `! DEMO CONFIGURATION — Cisco IOS-XE\n! In-memory sample; not generated or validated by V9\nhostname SW1\n!\nvlan 120\n name DEMO_USERS\n!\ninterface GigabitEthernet1/0/1\n description DEMO_ACCESS_PORT\n switchport mode access\n switchport access vlan 120\n!\nend\n`,
};

const sampleDocumentDevices: Array<{ configId: string; deviceId: string; hostname: string; vendor: Vendor; platform: string; version: string }> = [
  { configId: 'config-r1', deviceId: 'dev-r1', hostname: 'R1', vendor: 'cisco', platform: 'iosxe', version: '17.9' },
  { configId: 'config-r2', deviceId: 'dev-r2', hostname: 'R2', vendor: 'huawei', platform: 'vrp', version: '8' },
  { configId: 'config-r3', deviceId: 'dev-r3', hostname: 'R3', vendor: 'juniper', platform: 'junos', version: '23.4' },
  { configId: 'config-sw1', deviceId: 'lab-sw1', hostname: 'SW1', vendor: 'cisco', platform: 'iosxe', version: '17.9' },
];

export const demoDocuments: Record<string, EditorDocument> = Object.fromEntries(
  sampleDocumentDevices.map((device) => [
    device.configId,
    {
      id: device.configId,
      deviceId: device.deviceId,
      name: `${device.hostname.toLowerCase()}-${device.vendor}.cfg`,
      vendor: device.vendor,
      hostname: device.hostname,
      platform: device.platform,
      version: device.version,
      language: 'network-cli' as const,
      originalContent: sampleConfigurations[device.configId],
      content: sampleConfigurations[device.configId],
      dirty: false,
    },
  ]),
);

export const sampleDocumentIds = sampleDocumentDevices.map((device) => device.configId);

export const initialChatMessages: ChatMessage[] = [
  {
    id: 'welcome',
    role: 'assistant',
    content: 'Demo Copilot is ready. Messages stay in this browser session and are not sent to V9, Ollama, or FastAPI.',
    mock: true,
    createdAt: 'Demo session',
  },
];

export const initialActivity: ActivityEntry[] = [
  { id: 'activity-1', kind: 'system', message: 'Workbench shell initialized with local sample fixtures.', createdAt: 'Demo startup', simulated: true },
  { id: 'activity-2', kind: 'system', message: 'Mock chat, inventory and configurations remain isolated from the read-only backend status connection.', createdAt: 'Demo startup', simulated: true },
];

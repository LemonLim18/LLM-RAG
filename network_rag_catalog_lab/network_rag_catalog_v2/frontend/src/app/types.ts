import type { InventoryDevice } from '../services/inventoryApi';
import type { useLocalPlanning } from '../features/chat/useLocalPlanning';

export type Vendor = 'cisco' | 'huawei' | 'juniper';

export interface EditorDocument {
  id: string;
  deviceId: string;
  name: string;
  vendor: Vendor;
  hostname: string;
  platform: string;
  version: string;
  language: 'network-cli';
  originalContent: string;
  content: string;
  dirty: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  mock: boolean;
  createdAt: string;
}

export interface ActivityEntry {
  id: string;
  kind: 'system' | 'selection' | 'editor' | 'chat';
  message: string;
  createdAt: string;
  simulated: boolean;
}

export interface PanelLayout {
  explorerWidth: number;
  copilotWidth: number;
  activityHeight: number;
  explorerVisible: boolean;
  copilotVisible: boolean;
  activityVisible: boolean;
}

export interface WorkbenchState {
  devices: InventoryDevice[];
  selectedDeviceId: string;
  inventory: {
    phase: 'loading' | 'ready' | 'empty' | 'error';
    source: 'synthetic' | null;
    revision: string | null;
    message: string;
  };
  documents: Record<string, EditorDocument>;
  openTabIds: string[];
  activeTabId: string;
  chatMessages: ChatMessage[];
  activity: ActivityEntry[];
  layout: PanelLayout;
  workspaceView: 'samples' | 'plan' | 'preview' | 'original' | 'working';
  reviewSessionId: string;
  reviewSessionRevision: string;
  selectedPlanningTaskId: string;
  generatedPreview: GeneratedPreviewSelection | null;
  previewNotice: string;
}

// Presentation coordinates only: the provider's confirmed response owns content.
export interface GeneratedPreviewSelection {
  sessionId: string;
  sessionRevision: string;
  taskId: string;
  deviceId: string;
  configIndex: number;
}

export type WorkbenchAction =
  | { type: 'SELECT_DEVICE'; deviceId: string }
  | { type: 'INVENTORY_LOADING' }
  | { type: 'INVENTORY_LOADED'; devices: InventoryDevice[]; source: 'synthetic'; revision: string; selectDeviceId?: string }
  | { type: 'INVENTORY_FAILED'; message: string }
  | { type: 'ACTIVATE_TAB'; tabId: string }
  | { type: 'UPDATE_DOCUMENT'; tabId: string; content: string }
  | { type: 'SEND_MOCK_MESSAGE'; message: string }
  | { type: 'SHOW_WORKSPACE_VIEW'; view: WorkbenchState['workspaceView'] }
  | { type: 'SYNC_PLANNING_SESSION'; sessionId: string; sessionRevision: string; taskIds: string[] }
  | { type: 'OPEN_GENERATED_PREVIEW'; selection: GeneratedPreviewSelection }
  | { type: 'CLOSE_GENERATED_PREVIEW' }
  | { type: 'SELECT_PLANNING_TASK'; taskId: string }
  | { type: 'RESIZE_PANEL'; panel: 'explorer' | 'copilot' | 'activity'; value: number }
  | { type: 'TOGGLE_PANEL'; panel: 'explorer' | 'copilot' | 'activity' };

export interface WorkbenchContextValue {
  state: WorkbenchState;
  dispatch: React.Dispatch<WorkbenchAction>;
  retryInventory: () => void;
  refreshInventory: (selectDeviceId?: string) => Promise<import('../services/inventoryApi').InventoryListResponse>;
  localPlanning: ReturnType<typeof useLocalPlanning>;
  originals: ReturnType<typeof import('../features/workspace/useSavedOriginals').useSavedOriginals>;
  working: ReturnType<typeof import('../features/workspace/useWorkingDocuments').useWorkingDocuments>;
}

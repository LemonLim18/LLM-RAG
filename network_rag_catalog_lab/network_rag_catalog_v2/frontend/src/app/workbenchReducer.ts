import { demoDocuments, initialActivity, initialChatMessages, sampleDocumentIds } from '../fixtures/workbenchDemo';
import type { ActivityEntry, WorkbenchAction, WorkbenchState } from './types';

const timestamp = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
const activityId = () => `activity-${Date.now()}-${Math.random().toString(16).slice(2)}`;

function appendActivity(state: WorkbenchState, entry: Omit<ActivityEntry, 'id' | 'createdAt' | 'simulated'>): ActivityEntry[] {
  return [
    ...state.activity,
    { ...entry, id: activityId(), createdAt: timestamp(), simulated: true },
  ].slice(-80);
}

export const initialWorkbenchState: WorkbenchState = {
  devices: [],
  selectedDeviceId: '',
  inventory: { phase: 'loading', source: null, revision: null, message: 'Loading V9 demo inventory…' },
  documents: demoDocuments,
  openTabIds: sampleDocumentIds,
  activeTabId: sampleDocumentIds[0],
  chatMessages: initialChatMessages,
  activity: initialActivity,
  layout: {
    explorerWidth: 248,
    copilotWidth: 340,
    activityHeight: 190,
    explorerVisible: true,
    copilotVisible: true,
    activityVisible: true,
  },
  workspaceView: 'samples',
  reviewSessionId: '',
  reviewSessionRevision: '',
  selectedPlanningTaskId: '',
  generatedPreview: null,
  previewNotice: '',
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export function workbenchReducer(state: WorkbenchState, action: WorkbenchAction): WorkbenchState {
  switch (action.type) {
    case 'SELECT_DEVICE': {
      const device = state.devices.find((item) => item.id === action.deviceId);
      if (!device) return state;
      return {
        ...state,
        selectedDeviceId: device.id,
        activeTabId: Object.values(state.documents).find((document) => document.deviceId === device.id)?.id ?? state.activeTabId,
        workspaceView: 'samples',
        activity: appendActivity(state, { kind: 'selection', message: `Selected V9 demo inventory device ${device.hostname} (${device.vendor}).` }),
      };
    }
    case 'INVENTORY_LOADING':
      return { ...state, inventory: { phase: 'loading', source: null, revision: null, message: 'Loading V9 demo inventory…' } };
    case 'INVENTORY_LOADED': {
      const selectedDeviceId = action.selectDeviceId && action.devices.some((device) => device.id === action.selectDeviceId)
        ? action.selectDeviceId : action.devices.some((device) => device.id === state.selectedDeviceId)
        ? state.selectedDeviceId
        : action.devices[0]?.id ?? '';
      return {
        ...state,
        devices: action.devices,
        selectedDeviceId,
        inventory: {
          phase: action.devices.length ? 'ready' : 'empty',
          source: action.source,
          revision: action.revision,
          message: action.devices.length ? 'V9 demo inventory loaded' : 'The V9 demo inventory is empty.',
        },
      };
    }
    case 'INVENTORY_FAILED':
      return {
        ...state,
        devices: [],
        selectedDeviceId: '',
        inventory: { phase: 'error', source: null, revision: null, message: action.message },
      };
    case 'ACTIVATE_TAB':
      if (!state.openTabIds.includes(action.tabId)) return state;
      return { ...state, activeTabId: action.tabId, workspaceView: 'samples' };
    case 'UPDATE_DOCUMENT': {
      const document = state.documents[action.tabId];
      if (!document || document.content === action.content) return state;
      const becameDirty = !document.dirty && action.content !== document.originalContent;
      return {
        ...state,
        documents: {
          ...state.documents,
          [action.tabId]: { ...document, content: action.content, dirty: action.content !== document.originalContent },
        },
        activity: becameDirty
          ? appendActivity(state, { kind: 'editor', message: `Edited ${document.name}; working copy is local and unvalidated.` })
          : state.activity,
      };
    }
    case 'SEND_MOCK_MESSAGE': {
      const text = action.message.trim();
      if (!text) return state;
      const now = timestamp();
      return {
        ...state,
        chatMessages: [
          ...state.chatMessages,
          { id: `user-${Date.now()}`, role: 'user', content: text, mock: true, createdAt: now },
          { id: `assistant-${Date.now()}`, role: 'assistant', content: `Mock response: I received “${text}”. Backend status is read-only; this message was not sent to V9 or FastAPI.`, mock: true, createdAt: now },
        ],
        activity: appendActivity(state, { kind: 'chat', message: 'Added a local mock Copilot exchange.' }),
      };
    }
    case 'SHOW_WORKSPACE_VIEW':
      if (action.view === 'plan' && !state.reviewSessionId) return state;
      if (action.view === 'preview' && !state.generatedPreview) return state;
      return { ...state, workspaceView: action.view };
    case 'OPEN_GENERATED_PREVIEW':
      if (action.selection.sessionId !== state.reviewSessionId || action.selection.sessionRevision !== state.reviewSessionRevision) return state;
      return { ...state, generatedPreview: action.selection, previewNotice: '', workspaceView: 'preview' };
    case 'CLOSE_GENERATED_PREVIEW':
      return { ...state, generatedPreview: null, previewNotice: '', workspaceView: 'plan' };
    case 'SYNC_PLANNING_SESSION': {
      const sameSession = state.reviewSessionId === action.sessionId;
      const keepPreview = sameSession && state.reviewSessionRevision === action.sessionRevision
        && Boolean(state.generatedPreview && action.taskIds.includes(state.generatedPreview.taskId));
      const selectedPlanningTaskId = sameSession && action.taskIds.includes(state.selectedPlanningTaskId)
        ? state.selectedPlanningTaskId
        : action.taskIds[0] ?? '';
      return {
        ...state,
        reviewSessionId: action.sessionId,
        reviewSessionRevision: action.sessionRevision,
        selectedPlanningTaskId,
        workspaceView: 'plan',
        generatedPreview: keepPreview ? state.generatedPreview : null,
        previewNotice: state.generatedPreview && !keepPreview
          ? 'The previous V9 preview was closed because the confirmed session changed. Open an output from the current plan to review it.' : state.previewNotice,
      };
    }
    case 'SELECT_PLANNING_TASK':
      return { ...state, selectedPlanningTaskId: action.taskId };
    case 'RESIZE_PANEL': {
      const next = { ...state.layout };
      if (action.panel === 'explorer') next.explorerWidth = clamp(action.value, 190, 380);
      if (action.panel === 'copilot') next.copilotWidth = clamp(action.value, 280, 480);
      if (action.panel === 'activity') next.activityHeight = clamp(action.value, 120, 360);
      return { ...state, layout: next };
    }
    case 'TOGGLE_PANEL': {
      const key = `${action.panel}Visible` as const;
      return { ...state, layout: { ...state.layout, [key]: !state.layout[key] } };
    }
    default:
      return state;
  }
}

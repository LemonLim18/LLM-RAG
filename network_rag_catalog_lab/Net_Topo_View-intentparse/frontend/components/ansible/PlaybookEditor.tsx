import { languageForDocument } from '../../src/monacoLanguages';
import { useCapability } from '../../src/localLab';
import React, { useCallback, useState, useEffect, useLayoutEffect, useRef } from 'react';
import Editor, { DiffEditor } from '@monaco-editor/react';
import { aiApi, type EditorSnapshot, type EditProposal } from '../../src/services/ai';
import { applyWorkspaceChanges, openDocumentModel } from '../../src/utils/workspaceProposal';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  X, Save, Download, Play, ShieldCheck, RefreshCw, FlaskConical, Lock, FileText, Check, Loader2, MessageSquareQuote
} from 'lucide-react';
import type { AnsibleTab, AnsibleJob, AnsibleCheckResult } from '../../typesLLM';
import { useMonacoTheme } from '../../src/utils/monacoTheme';

interface PlaybookEditorProps {
  onEditableCopy?: () => void;
  onEditorBridge?: (bridge: EditorBridge | null) => void;
  onDocumentDevice?: (id: string, deviceId: string) => void;
  tabs:            AnsibleTab[];
  activeTabId:     string | null;
  job:             AnsibleJob | null;
  checkResult?:    AnsibleCheckResult | null;
  isChecking?:     boolean;
  approvalReady?:  boolean;
  userRole:        string;
  onTabSelect:     (id: string) => void;
  onTabClose:      (id: string) => void;
  onChange:        (id: string, content: string) => void;
  onBatchChange?: (changes:{id:string;content:string;isDirty:boolean}[])=>void;
  onSave:          (id: string) => void;
  onCheck:         () => void;
  onApprove:       () => void;
  onDeploy:        () => void;
  onRegenerate:    () => void;
  onExplainSelection?: (payload: { text: string; tab: AnsibleTab }) => void;
}

export interface EditorBridge {
  snapshot: () => EditorSnapshot | null;
  relatedSnapshots: () => EditorSnapshot[];
  review: (proposal: EditProposal) => boolean;
}


/** Helper to prefix generic names (playbook.yml, main.yml) with job_ID parent for clarity */
const getDisplayName = (tab: AnsibleTab) => {
  if (tab.name !== 'playbook.yml' && tab.name !== 'main.yml') return tab.name;
  const path = (tab.path || tab.id || '').replace(/\\/g, '/');
  const parts = path.split('/');
  if (parts.length >= 2) {
    const parent = parts[parts.length - 2];
    if (parent.startsWith('job_')) return `${parent}/${tab.name}`;
  }
  return tab.name;
};

const PlaybookEditor: React.FC<PlaybookEditorProps> = ({
  tabs, activeTabId, job, checkResult: _checkResult = null, isChecking = false,
  approvalReady = false,
  userRole,   onTabSelect, onTabClose, onChange, onSave,
  onCheck, onApprove, onDeploy, onRegenerate,
  onExplainSelection,
  onEditorBridge,
  onDocumentDevice, onEditableCopy,onBatchChange,
}) => {
  const executionAvailable = useCapability('execution.deploy');
  const aiAvailable = useCapability('ai.generate');
  const approvalAvailable = useCapability('approval.workflow_ui');
  const { themeName } = useMonacoTheme();
  const activeTabRef = useRef<HTMLDivElement>(null);
  const editorInstanceRef = useRef<any>(null);
  const monacoRef=useRef<any>(null);
  const allTabs=useRef(tabs);allTabs.current=tabs;
  const editorContainerRef = useRef<HTMLDivElement>(null);
  const selectionDisposeRef = useRef<{ dispose?: () => void } | null>(null);
  const activeTab = tabs.find(t => t.id === activeTabId) ?? null;
  const [proposal, setProposal] = useState<EditProposal | null>(null);
  const [reviewPath,setReviewPath]=useState('');
  const [undoBundle,setUndoBundle]=useState<EditProposal|null>(null);
  const [applyingBundle,setApplyingBundle]=useState(false);
  const reviewEditor = useRef<any>(null);
  const detachReview = useCallback(() => {
    const editor = reviewEditor.current; reviewEditor.current = null;
    const models = editor?.getModel();
    if (models) { editor.setModel(null); models.original.dispose(); models.modified.dispose(); }
  }, []);
  const dismissReview = useCallback(() => { detachReview(); setProposal(null); }, [detachReview]);
  useLayoutEffect(() => () => detachReview(), [detachReview]);
  const [reviewError, setReviewError] = useState('');
  const [documentDevices, setDocumentDevices] = useState<{id: number; hostname: string}[]>([]);
  useEffect(() => {
    if (onDocumentDevice) void aiApi.inventory().then(r => setDocumentDevices(r.data.devices)).catch(() => setDocumentDevices([]));
  }, [onDocumentDevice]);
  const epoch = useRef(0);
  const currentTab = useRef(activeTab);
  currentTab.current = activeTab;
  const changeDispose = useRef<{ dispose: () => void } | null>(null);
  const snapshot = useCallback((): EditorSnapshot | null => {
    const editor = editorInstanceRef.current; const tab = currentTab.current;
    const model = editor?.getModel();
    if (!model || !tab || model.isDisposed()) return null;
    if (!decodeURIComponent(model.uri.path).endsWith('/' + tab.path)) return null;
    const selected = editor.getSelection();
    return { document_id: tab.id, path: tab.path, content: model.getValue(undefined, true), language: model.getLanguageId(),
      model_id: model.id, model_version: model.getVersionId(), buffer_epoch: epoch.current,
      saved_revision: tab.savedRevision ?? 0, is_dirty: tab.isDirty, read_only: tab.isReadOnly,
      device_id: tab.deviceId,
      ...(selected && !selected.isEmpty() ? { selection: { text: model.getValueInRange(selected), start_line: selected.startLineNumber, end_line: selected.endLineNumber } } : {}) };
  }, []);
  const matches = useCallback((p: EditProposal) => {
    const now = snapshot();
    return !!now && now.document_id === p.document_id && now.path === p.path && now.model_id === p.model_id &&
      now.model_version === p.model_version && now.buffer_epoch === p.buffer_epoch && now.saved_revision === p.saved_revision && now.content === p.original && !now.read_only;
  }, [snapshot]);
  const modelFor=useCallback((path:string)=>{
    const monaco=monacoRef.current;
    if(!monaco)return null;
    // Restored inactive tabs have unsaved text before Monaco lazily mounts them.
    // Materialize only an already-open document, using the same URI as Editor.
    // Never reload its saved file or replace an existing (possibly newer) model.
    return openDocumentModel(path,allTabs.current,
      key=>monaco.editor.getModel(monaco.Uri.parse(key)),
      (key,content)=>monaco.editor.createModel(content,languageForDocument(key,content),monaco.Uri.parse(key)));
  },[]);
  const snapshotFor=useCallback((path:string):EditorSnapshot|null=>{
    if(currentTab.current?.path===path)return snapshot();
    const tab=allTabs.current.find(t=>t.path===path),model=modelFor(path);
    if(!tab||!model)return null;
    return {document_id:tab.id,path:tab.path,content:model.getValue(undefined,true),language:model.getLanguageId(),model_id:model.id,
      model_version:model.getVersionId(),buffer_epoch:epoch.current,saved_revision:tab.savedRevision??0,is_dirty:tab.isDirty,read_only:tab.isReadOnly,device_id:tab.deviceId};
  },[snapshot,modelFor]);
  const relatedSnapshots=useCallback(()=>{
    const content=snapshot()?.content||'';
    const score=(tab:AnsibleTab)=>Number(content.includes(tab.path)||content.includes(tab.path.split('/').pop()||'\u0000'));
    return [...allTabs.current].reverse().filter(t=>t.path!==currentTab.current?.path && /^(playbooks|roles|reference|Test_Reference)\//.test(t.path)).sort((a,b)=>score(b)-score(a)).slice(0,8).map(t=>snapshotFor(t.path)).filter((s):s is EditorSnapshot=>!!s);
  },[snapshotFor,snapshot]);
  const bundleMatches=useCallback((p:EditProposal)=>matches(p) && (p.files||[]).every(file=>{
    const now=snapshotFor(file.path);
    return !!now && !now.read_only && now.document_id===file.document_id && now.model_id===file.model_id && now.model_version===file.model_version && now.buffer_epoch===file.buffer_epoch && now.saved_revision===file.saved_revision && now.content===file.original;
  }),[matches,snapshotFor]);
  useEffect(() => {
    onEditorBridge?.({ snapshot,relatedSnapshots, review: p => {
      if (!bundleMatches(p) || !p.files?.length && p.original === p.suggested) return false;
      setReviewError('');setReviewPath(p.files?.[0]?.path||p.path); setProposal(p); return true;
    } });
    return () => onEditorBridge?.(null);
  }, [onEditorBridge, snapshot, bundleMatches,relatedSnapshots]);
  useEffect(() => { epoch.current++; dismissReview(); setReviewError(''); }, [activeTabId, activeTab?.deviceId, dismissReview]);
  useEffect(() => () => changeDispose.current?.dispose(), []);
  const acceptProposal = async () => {
    if(proposal?.files?.length){
      if(!bundleMatches(proposal)){setReviewError('The coordinated proposal is stale. Every buffer was preserved.');return;}
      const files=proposal.files;
      const before=files.map(file=>({id:file.document_id,content:file.original,isDirty:allTabs.current.find(t=>t.id===file.document_id)?.isDirty||false}));
      setApplyingBundle(true);
      try{
        const checks=[...new Set([proposal.path,...files.map(f=>f.path)])].map(path=>snapshotFor(path)).filter((s):s is EditorSnapshot=>!!s);
        await aiApi.checkRevisions(checks);
        if(!bundleMatches(proposal))throw Error('A workspace buffer changed during revision verification. Nothing was applied.');
        applyWorkspaceChanges(files,modelFor);
        onBatchChange?.(files.map(file=>({id:file.document_id,content:file.suggested,isDirty:true})));
        setUndoBundle(proposal);dismissReview();setReviewError('');
      }catch(error){
        onBatchChange?.(before.map(file=>{const text=modelFor(files.find(f=>f.document_id===file.id)!.path)?.getValue(undefined,true)??file.content;return {...file,content:text,isDirty:text===file.content?file.isDirty:true};}));
        setReviewError(error instanceof Error?error.message:String(error));
      }
      finally{setApplyingBundle(false);}
      return;
    }
    if (!proposal || !matches(proposal)) { setReviewError('This proposal is stale. Your current buffer was preserved. Request a new edit.'); return; }
    const next = proposal.suggested;
    const eols: string[] = next.match(/\r\n|\r|\n/g) || [];
    if (new Set(eols).size > 1 || eols.includes('\r') || next.startsWith('\uFEFF') !== proposal.original.startsWith('\uFEFF')) {
      setReviewError('Mixed line endings or a changed BOM require manual review. Nothing was applied.'); return;
    }
    const editor = editorInstanceRef.current; const model = editor.getModel(); const view = editor.saveViewState();
    editor.updateOptions({ readOnly: false, domReadOnly: false });
    editor.pushUndoStop();
    if (eols.length && model.getEOL() !== eols[0]) model.pushEOL(eols[0] === '\r\n' ? 1 : 0);
    const applied = editor.executeEdits('accept-ai-proposal', [{ range: model.getFullModelRange(), text: next.replace(/^\uFEFF/, '') }]);
    editor.pushUndoStop(); editor.restoreViewState(view);
    if (applied) { dismissReview(); setReviewError(''); editor.focus(); }
    else setReviewError('Monaco refused the edit. The proposal was not accepted.');
  };
  const undoCoordinated=async()=>{
    if(!undoBundle?.files)return;
    const files=undoBundle.files;
    setApplyingBundle(true);
    try{
      const checks=files.map(file=>snapshotFor(file.path));
      if(checks.some((s,i)=>!s||s.read_only||s.content!==files[i].suggested||s.saved_revision!==files[i].saved_revision))throw Error('The workspace changed after acceptance. Group undo was not applied; use the individual editor undo controls.');
      await aiApi.checkRevisions(checks as EditorSnapshot[]);
      applyWorkspaceChanges(files.map(f=>({path:f.path,original:f.suggested,suggested:f.original})),modelFor);
      onBatchChange?.(files.map(file=>({id:file.document_id,content:file.original,isDirty:true})));
      setUndoBundle(null);setReviewError('');
    }catch(error){setReviewError(error instanceof Error?error.message:String(error));}
    finally{setApplyingBundle(false);}
  };
  const isMarkdownActiveTab = Boolean(activeTab?.name.toLowerCase().endsWith('.md'));
  const canEdit   = userRole === 'admin' || userRole === 'engineer';
  const [selectionAction, setSelectionAction] = useState<{ text: string; top: number; left: number } | null>(null);
  
  // Auto-scroll active tab into view
  useEffect(() => {
    if (activeTabRef.current) {
      activeTabRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      });
    }
  }, [activeTabId, tabs.length]);

  // Only show markdown preview when user explicitly chooses Preview (right-click or toolbar)
  const [mdPreviewTabId, setMdPreviewTabId] = useState<string | null>(null);
  const isMdPreview = !!activeTab?.name.endsWith('.md') && mdPreviewTabId === activeTab.id;
  const toggleMdPreview = useCallback(() => {
    if (!activeTab?.name.endsWith('.md')) return;
    setMdPreviewTabId((id) => (id === activeTab.id ? null : activeTab.id));
  }, [activeTab?.id, activeTab?.name]);

  const [tabContextMenu, setTabContextMenu] = useState<{ x: number; y: number; tabId: string } | null>(null);
  const openTabContextMenu = useCallback((e: React.MouseEvent, tabId: string) => {
    e.preventDefault();
    e.stopPropagation();
    const tab = tabs.find((t) => t.id === tabId);
    if (tab?.name.endsWith('.md')) setTabContextMenu({ x: e.clientX, y: e.clientY, tabId });
  }, [tabs]);
  const closeTabContextMenu = useCallback(() => setTabContextMenu(null), []);

  const handleDownload = useCallback(() => {
    if (!activeTab) return;
    const blob = new Blob([activeTab.content], { type: 'text/yaml' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = activeTab.name;
    a.click();
    URL.revokeObjectURL(url);
  }, [activeTab]);

  const clearSelectionAction = useCallback(() => setSelectionAction(null), []);

  const updateSelectionAction = useCallback(() => {
    const editor = editorInstanceRef.current;
    const tab = activeTab;
    const host = editorContainerRef.current;
    if (!editor || !tab || !host || tab.name.endsWith('.md')) {
      setSelectionAction(null);
      return;
    }
    const selection = editor.getSelection?.();
    const model = editor.getModel?.();
    if (!selection || !model || selection.isEmpty?.()) {
      setSelectionAction(null);
      return;
    }
    const text = String(model.getValueInRange?.(selection) || '').trim();
    if (!text) {
      setSelectionAction(null);
      return;
    }
    const pos = editor.getScrolledVisiblePosition?.(selection.getEndPosition?.());
    if (!pos) {
      setSelectionAction({ text, top: 12, left: 12 });
      return;
    }
    const hostRect = host.getBoundingClientRect();
    const estimatedWidth = 150;
    const desiredLeft = pos.left + Math.min(pos.width || 0, 24);
    const left = Math.max(12, Math.min(desiredLeft, hostRect.width - estimatedWidth - 12));
    const top = Math.max(12, pos.top - 34);
    setSelectionAction({ text, top, left });
  }, [activeTab]);

  useEffect(() => {
    clearSelectionAction();
  }, [activeTabId, clearSelectionAction]);

  useEffect(() => {
    return () => {
      selectionDisposeRef.current?.dispose?.();
    };
  }, []);

  // Derive action states
  const hasPlaybook = !!activeTab?.jobId;
  const normalizedStatus = String(job?.status || '').trim().toLowerCase();
  const normalizedStage = String(job?.stage || '').trim().toLowerCase();
  const isApproved  = normalizedStatus === 'approved';
  const isPendingApproval =
    (normalizedStatus === 'pending' && normalizedStage === 'approve') ||
    normalizedStatus === 'pending_approval' ||
    normalizedStatus === 'submitted';
  const isRejected  = normalizedStatus === 'rejected';
  const isDeploying = normalizedStatus === 'running';
  const isDone      = normalizedStatus === 'success' || normalizedStatus === 'failed';
  const hasExecutedBefore = isDone;
  const isEngineer  = userRole === 'engineer';
  const canRunCheck = hasPlaybook && !isChecking && !isDeploying && !isMarkdownActiveTab && (!isEngineer || isApproved || isDone);
  const checkTitle = isMarkdownActiveTab
    ? 'Check is only available for playbook YAML files'
    : (isEngineer && !isApproved && !isDone
        ? 'Playbook must be approved by an administrator before it can be dry-run (checked)'
        : 'Dry-run (--check --diff) — results appear in Output tab');
  // Terminal states for the primary "Send" flow (but pending queue still allows Resend).
  const approveDone = isApproved || isDeploying || isDone;
  // Allow re-deploy when a job was already approved at least once.
  // Backend enforces "must be approved" for execution, but historically jobs may
  // move to success/failed status after the first run; we still want Deploy to stay available.
  const canDeploy = isApproved || isDone;
  const canSubmitToQueue =
    canEdit &&
    hasPlaybook &&
    (isEngineer ? true : approvalReady) &&
    !isApproved &&
    !isDeploying;
  const approveTitle = isPendingApproval
    ? (isEngineer
        ? 'Resend this playbook to the Approval Queue'
        : (approvalReady
            ? 'Submit again to refresh the queue entry and audit trail (same playbook must still pass Check)'
            : 'Run Check (rc=0) before resending to the Approval Queue'))
    : (isEngineer
        ? 'Send this playbook to the Approval Queue'
        : (!approvalReady ? 'Run Check (rc=0) to enable Send for Approval' : 'Send this playbook to Approval Queue'));
  const deployTitle = !canDeploy
    ? 'Job must be approved by an admin first'
    : 'Deploy to all target devices';

  return (
    <div className="flex flex-col h-full min-h-0 bg-base-200">

      {/* ── Tab bar ───────────────────────────────────────────────────── */}
      <div className="flex items-center gap-0 bg-base-100 border-b border-base-300 overflow-x-auto shrink-0 min-h-[38px]">
        {tabs.length === 0 && (
          <span className="px-4 text-xs opacity-40 italic">No files open — click a file or generate a playbook</span>
        )}
        {tabs.map(tab => (
          <div
            key={tab.id}
            ref={tab.id === activeTabId ? activeTabRef : null}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs border-r border-base-300 cursor-pointer shrink-0 transition-colors ${
              tab.id === activeTabId
                ? 'bg-base-200 text-base-content font-semibold'
                : 'hover:bg-base-200 opacity-60'
            }`}
            onClick={() => { closeTabContextMenu(); onTabSelect(tab.id); }}
            onContextMenu={(e) => openTabContextMenu(e, tab.id)}
          >
            {tab.isReadOnly && <Lock className="h-3 w-3 opacity-40" />}
            <span className="max-w-40 truncate" title={tab.path || tab.id}>{getDisplayName(tab)}</span>
            {tab.isDirty && <span className="w-1.5 h-1.5 rounded-full bg-warning shrink-0" title="Unsaved changes" />}
            <button
              className="hover:text-error ml-0.5 opacity-50 hover:opacity-100"
              onClick={e => { e.stopPropagation(); onTabClose(tab.id); }}
              title="Close"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
        {tabContextMenu && (
          <>
            <div className="fixed inset-0 z-40" onClick={closeTabContextMenu} onContextMenu={closeTabContextMenu} aria-hidden="true" />
            <div
              className="fixed z-50 min-w-[140px] py-1 bg-base-200 border border-base-300 rounded-lg shadow-xl"
              style={{ left: tabContextMenu.x, top: tabContextMenu.y }}
            >
              <button
                type="button"
                className="w-full px-3 py-1.5 text-left text-xs hover:bg-base-300 flex items-center gap-2"
                onClick={() => {
                  if (tabContextMenu.tabId !== activeTabId) onTabSelect(tabContextMenu.tabId);
                  setMdPreviewTabId(tabContextMenu.tabId);
                  closeTabContextMenu();
                }}
              >
                <FileText className="h-3 w-3" /> Preview
              </button>
              {mdPreviewTabId === tabContextMenu.tabId && (
                <button
                  type="button"
                  className="w-full px-3 py-1.5 text-left text-xs hover:bg-base-300 flex items-center gap-2"
                  onClick={() => { setMdPreviewTabId(null); closeTabContextMenu(); }}
                >
                  Close Preview
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {/* ── Action bar ────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-base-100 border-b border-base-300 shrink-0 flex-wrap">
        <button
          className="btn btn-xs btn-ghost gap-1"
          onClick={onRegenerate}
          disabled={!aiAvailable || !hasPlaybook}
          title="Re-generate playbook via AI"
        >
          <RefreshCw className="h-3 w-3" /> Re-generate
        </button>

        <div className="divider divider-horizontal mx-0 my-0 h-5" />

        <button
          className="btn btn-xs btn-info gap-1"
          onClick={onCheck}
          disabled={!executionAvailable || !canRunCheck}
          title={checkTitle}
        >
          {isChecking ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              Checking...
            </>
          ) : (
            <>
              <FlaskConical className="h-3 w-3" />
              Check
            </>
          )}
        </button>

        <button
          className={`btn btn-xs gap-1 ${
            isPendingApproval
              ? (isEngineer || approvalReady)
                ? 'btn-outline btn-warning'
                : 'btn-success'
              : approveDone
                ? 'btn-success'
                : (isEngineer || approvalReady)
                  ? 'btn-warning'
                  : 'btn-ghost opacity-60'
          }`}
          onClick={onApprove}
          disabled={!approvalAvailable || !canSubmitToQueue}
          title={approveTitle}
        >
          {isPendingApproval ? (
            (isEngineer || approvalReady) ? <RefreshCw className="h-3 w-3" /> : <Check className="h-3 w-3" />
          ) : approveDone ? (
            <Check className="h-3 w-3" />
          ) : (
            <ShieldCheck className="h-3 w-3" />
          )}
          {isPendingApproval
            ? (isEngineer || approvalReady)
              ? 'Resend to Queue'
              : 'Sent for Approval'
            : approveDone
              ? 'Approved'
              : 'Send for Approval'}
        </button>

        <button
          className={`btn btn-xs gap-1 ${isDeploying ? 'btn-disabled' : 'btn-success'}`}
          onClick={onDeploy}
          disabled={!executionAvailable || !canEdit || !canDeploy || isDeploying}
          title={deployTitle}
        >
          <Play className="h-3 w-3" />
          {isDeploying ? 'Deploying…' : hasExecutedBefore ? 'Re-Deploy' : 'Deploy'}
        </button>

        {/* {!isAdmin && hasPlaybook && !isApproved && !isRejected && (
          <span className="badge badge-warning badge-sm">Awaiting Queue Review</span>
        )} */}
        {isRejected && (
          <span className="badge badge-error badge-sm" title="Rejected by admin review">
            Rejected
          </span>
        )}
        {activeTab?.isReadOnly && (
          <span
            className="badge badge-ghost badge-sm gap-1"
            title={job?.lockedReason || 'This file is read-only'}
          >
            <Lock className="h-3 w-3" />
            {job?.readOnly ? 'Approved read-only' : 'Read-only'}
          </span>
        )}

        <div className="ml-auto flex items-center gap-2">
          {onDocumentDevice && activeTab && /\.(cfg|conf|txt|log)$/i.test(activeTab.name) && <select aria-label="Document device" className="select select-xs max-w-44" value={activeTab.deviceId || ''} disabled={Boolean(proposal)} onChange={e => onDocumentDevice(activeTab.id,e.target.value)}><option value="">Select document device</option>{documentDevices.map(device => <option key={device.id} value={String(device.id)}>{device.hostname}</option>)}</select>}
          {activeTab?.name.endsWith('.md') && (
            <button
              type="button"
              className={`btn btn-xs gap-1 ${isMdPreview ? 'btn-ghost bg-base-300' : 'btn-ghost'}`}
              onClick={toggleMdPreview}
              title={isMdPreview ? 'Close preview' : 'Open preview'}
            >
              <FileText className="h-3 w-3" /> {isMdPreview ? 'Close Preview' : 'Preview'}
            </button>
          )}
          {onEditableCopy && activeTab?.isReadOnly && <button className="btn btn-xs btn-outline" onClick={onEditableCopy}>Edit a copy</button>}
          {activeTab && !activeTab.isReadOnly && canEdit && (
            <button
              className={`btn btn-xs gap-1 ${
                activeTab.isDirty
                  ? 'btn-primary'
                  : 'bg-transparent border border-primary text-primary pointer-events-none'
              }`}
              onClick={activeTab.isDirty ? () => onSave(activeTab.id) : undefined}
              title={activeTab.isDirty ? 'Save file to disk' : 'Saved'}
            >
              <Save className={`h-3 w-3 ${activeTab.isDirty ? '' : 'text-primary'}`} /> {activeTab.isDirty ? 'Save' : 'Saved'}
            </button>
          )}
          {activeTab && (
            <button
              className="btn btn-xs btn-ghost gap-1"
              onClick={handleDownload}
              title="Download file"
            >
              <Download className="h-3 w-3" /> Download
            </button>
          )}
        </div>
      </div>

      {/* ── Editor or Markdown preview (preview only when user chooses Preview) ── */}
      <div className="grow min-h-0 overflow-auto">
        {activeTab ? (
          activeTab.name.endsWith('.md') && isMdPreview ? (
            <div className="p-4 min-h-full bg-base-300 text-base-content overflow-auto">
              <article className="prose prose-sm prose-invert max-w-none prose-headings:text-base-content prose-p:text-base-content/90 prose-li:text-base-content/90 prose-strong:text-base-content prose-code:bg-base-200 prose-code:text-base-content prose-pre:bg-base-200 prose-pre:text-base-content prose-blockquote:border-base-content/30 prose-blockquote:text-base-content/80">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {activeTab.content}
                </ReactMarkdown>
              </article>
            </div>
          ) : (
            <div ref={editorContainerRef} className="relative h-full" style={{ display: proposal ? 'none' : undefined }}>
              {selectionAction && activeTab && onExplainSelection && (
                <button
                  type="button"
                  className="absolute z-20 btn btn-xs btn-primary gap-1 shadow-lg"
                  style={{ top: selectionAction.top, left: selectionAction.left }}
                  onClick={() => {
                    onExplainSelection({ text: selectionAction.text, tab: activeTab });
                    clearSelectionAction();
                  }}
                >
                  <MessageSquareQuote className="h-3 w-3" />
                  Add to chat
                </button>
              )}
              <Editor
                keepCurrentModel
                path={activeTab.path}
                height="100%"
                language={languageForDocument(activeTab.path, activeTab.content)}
                theme={themeName}
                value={activeTab.content}
                onMount={(editor,monaco) => {
                  monacoRef.current=monaco;
                  selectionDisposeRef.current?.dispose?.();
                  editorInstanceRef.current = editor;
                  changeDispose.current?.dispose();
                  changeDispose.current = editor.onDidChangeModelContent(() => { epoch.current++; });
                  selectionDisposeRef.current = editor.onDidChangeCursorSelection(() => {
                    window.requestAnimationFrame(updateSelectionAction);
                  });
                  editor.onDidBlurEditorText?.(() => {
                    window.setTimeout(() => {
                      if (document.activeElement?.closest?.('.btn')) return;
                      clearSelectionAction();
                    }, 120);
                  });
                }}
                onChange={val => {
                  if (!activeTab.isReadOnly) onChange(activeTab.id, val ?? '');
                }}
                options={{
                  readOnly:         activeTab.isReadOnly || Boolean(proposal),
                  domReadOnly:      activeTab.isReadOnly,
                  minimap:          { enabled: false },
                  wordWrap:         'on',
                  fontSize:         13,
                  lineNumbers:      'on',
                  scrollBeyondLastLine: false,
                  automaticLayout:  true,
                  tabSize:          2,
                  renderWhitespace: 'boundary',
                  folding:          true,
                }}
              />
            </div>
          )
        ) : (
          <div className="flex flex-col items-center justify-center h-full opacity-30 gap-3">
            <FlaskConical className="h-10 w-10" />
            <span className="text-sm">Open a file from the explorer or generate a playbook via the AI chat</span>
          </div>
        )}
        {!proposal && undoBundle && <div className="p-2 flex items-center gap-2 border-t border-base-300"><span className="text-xs grow">Coordinated changes are unsaved.</span><button className="btn btn-sm" disabled={applyingBundle} onClick={undoCoordinated}>Undo coordinated changes</button></div>}
        {!proposal && reviewError && <p role="alert" className="text-error p-2">{reviewError}</p>}
        {proposal && <div className="h-full flex flex-col" aria-label="Review AI changes">
          <div className="p-2 border-b border-base-300 flex gap-2 items-center"><strong className="text-sm">Review proposed changes</strong><span className="text-xs opacity-60 grow">{proposal.files?.length?`${proposal.files.length} files. `:''}Accept changes buffers. Save is separate.</span><button className="btn btn-success btn-sm" disabled={applyingBundle} onClick={acceptProposal}>{proposal.files?.length?'Accept all':'Accept'}</button><button className="btn btn-ghost btn-sm" disabled={applyingBundle} onClick={() => { dismissReview(); setReviewError(''); }}>{proposal.files?.length?'Reject all':'Reject'}</button></div>
          {proposal.files && <div className="flex gap-1 p-1 overflow-x-auto" aria-label="Coordinated proposal files">{proposal.files.map(file=><button key={file.path} className={`btn btn-xs ${reviewPath===file.path?'btn-primary':''}`} onClick={()=>setReviewPath(file.path)}>{file.path}</button>)}</div>}
          {reviewError && <p role="alert" className="text-error p-2">{reviewError}</p>}
          <pre className="text-xs p-2 max-h-24 overflow-auto">{JSON.stringify(proposal.validation, null, 2)}</pre>
          <div className="grow min-h-0"><DiffEditor key={reviewPath||proposal.path} onMount={editor => { reviewEditor.current = editor; }} original={(proposal.files?.find(f=>f.path===reviewPath)||proposal).original} modified={(proposal.files?.find(f=>f.path===reviewPath)||proposal).suggested} theme={themeName} language={languageForDocument(reviewPath||proposal.path, (proposal.files?.find(f=>f.path===reviewPath)||proposal).suggested)} originalModelPath={`ai-review/${proposal.id}/${reviewPath}/base`} modifiedModelPath={`ai-review/${proposal.id}/${reviewPath}/proposal`} options={{ readOnly: true, originalEditable: false, renderSideBySide: false, automaticLayout: true }} /></div>
        </div>}
      </div>
    </div>
  );
};

export default PlaybookEditor;

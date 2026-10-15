import { useEffect, useMemo, useState } from 'react';
import './KnowledgeEngineering.css';
import KnowledgeLayouts from './knowledge/KnowledgeLayouts';
import { referenceSnapshot, latestReferenceSnapshot } from './knowledge/referenceData';
import { AlertTriangle, Database, GitBranch, Library, RefreshCw, Save, ShieldCheck, Sparkles, X } from 'lucide-react';
import { knowledgeApi } from '../src/services/api';
import { Toast } from '../src/utils/swal';

import { normalizeUserRole, type User, type ViewId } from '../types';

type Row = Record<string, any>;
type Page = 'Overview' | 'Categories' | 'Operations' | 'Parameters' | 'Templates' | 'Publication';
type Snapshot = { revision: string; data: { initialized: boolean; catalogs: Record<string, Row[]>; templates: Record<string, string>; active_release?: Record<string, any>; history: Row[]; releases?: Row[]; changes?: Row[]; authority?: string; publication_mode?: string; output_format?: string } };
const input = 'input input-bordered input-sm w-full bg-base-100';
const select = 'select select-bordered select-sm w-full bg-base-100';
const card = 'ke-card rounded-xl border border-base-300 bg-base-100 shadow-sm';
const split = (value: string) => value.split(',').map(item => item.trim()).filter(Boolean);
const titleCase = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());

function Badge({children, tone = 'neutral'}: {children: React.ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'info' | 'error'}) {
  const colors = {neutral: 'badge-ghost', success: 'badge-success', warning: 'badge-warning', info: 'badge-info', error: 'badge-error'};
  return <span className={`badge badge-sm ${colors[tone]}`}>{children}</span>;
}
function Empty({icon: Icon = Library, title, text}: {icon?: any; title: string; text: string}) {
  return <div className="flex min-h-44 flex-col items-center justify-center rounded-xl border border-dashed border-base-300 bg-base-200/30 px-6 text-center"><Icon className="mb-3 h-8 w-8 text-base-content/30"/><div className="font-semibold">{title}</div><p className="mt-1 max-w-md text-sm opacity-60">{text}</p></div>;
}
function PageHeader({icon: Icon, title, description, actions}: {icon: any; title: string; description: string; actions?: React.ReactNode}) {
  return <header className="ke-header flex flex-wrap items-start justify-between gap-4"><div className="flex items-start gap-3"><div className="rounded-xl bg-primary/15 p-2.5 text-primary"><Icon className="h-6 w-6"/></div><div><h1 className="text-2xl font-bold tracking-tight">{title}</h1><p className="mt-1 text-sm opacity-60">{description}</p></div></div>{actions && <div className="flex flex-wrap gap-2">{actions}</div>}</header>;
}
export default function KnowledgeEngineeringView({user, initialPage = 'Operations', setView, previewOnly = false}: {previewOnly?: boolean; user: User | null; initialPage?: Page; setView?: (view: ViewId) => void}) {
  const [storedSnapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [preview, setPreviewState] = useState(() => previewOnly || sessionStorage.getItem('knowledge_reference_preview') === 'true');
  const snapshot: Snapshot | null = preview ? (initialPage === 'Templates' ? referenceSnapshot : latestReferenceSnapshot) : storedSnapshot;
  function setPreview(value: boolean) { if (previewOnly) return; sessionStorage.setItem('knowledge_reference_preview', String(value)); setPreviewState(value); setSelectedCategory(''); setSelectedOperation(''); setSelectedParameter(''); setEditorMode('none'); setValidation(null); }
  const [busy, setBusy] = useState(true);
  const [reason, setReason] = useState('');
  const [actionError, setActionError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedParameter, setSelectedParameter] = useState('');
  const [selectedOperation, setSelectedOperation] = useState('');
  const [record, setRecord] = useState<Row>({});
  const [editorMode, setEditorMode] = useState<'none' | 'category' | 'parameter' | 'operation'>('none');
  const [mappings, setMappings] = useState<Row[]>([]);
  const [rules, setRules] = useState<Row[]>([]);
  const [schema, setSchema] = useState('');
  const [selectedTemplatePath, setSelectedTemplatePath] = useState('');
  const [templateContent, setTemplateContent] = useState('');
  const [newVariant, setNewVariant] = useState(false);
  const [variant, setVariant] = useState({vendor: 'cisco', platform: 'iosxe', versions: '17.9'});
  const [validation, setValidation] = useState<any>(null);

  const role = normalizeUserRole(user?.role);
  const editable = role === 'admin' || role === 'engineer';
  const catalogs = snapshot?.data.catalogs || {};
  const categories = catalogs.categories || [], parameters = catalogs.parameters || [], operations = catalogs.operations || [];
  const categoryParameters = catalogs.category_parameters || [], templateBindings = catalogs.template_bindings || [];
  const operationParameters = catalogs.operation_parameters || [], operationRules = catalogs.operation_rules || [];
  const activeRelease = snapshot?.data.active_release?.release_id || snapshot?.data.active_release?.version || 'Not published';

  async function load(showToast = false) {
    setBusy(true);
    try { const result = await knowledgeApi.inspect() as Snapshot; setSnapshot(result); if (showToast) Toast.success('Knowledge refreshed', 'Loaded the latest SQLite authoring state.'); return result; }
    catch (error: any) { Toast.error('Knowledge load failed', error.message || 'The knowledge service is unavailable.'); }
    finally { setBusy(false); }
  }
  async function mutate(action: () => Promise<any>, success: string) {
    if (preview) { Toast.warning('Reference-data preview', 'Switch to the live catalog to save changes.'); return false; }
    if (!reason.trim()) { Toast.warning('Change reason required', 'Describe why you are making this authoring change.'); return false; }
    setBusy(true);
    try { setActionError(''); await action(); setValidation(null); await load(); Toast.success(success); return true; }
    catch (error: any) { setActionError(error.message || String(error)); Toast.error('Knowledge change rejected', error.message || String(error)); setBusy(false); return false; }
  }
  useEffect(() => { if (!preview) void load(); else setBusy(false); }, [preview]);
  useEffect(() => { setSearch(''); setEditorMode('none'); }, [initialPage]);
  useEffect(() => { if (!snapshot?.data.initialized) return; if (!selectedCategory && categories[0]) setSelectedCategory(categories[0].category_id); if (!selectedParameter && parameters[0]) setSelectedParameter(parameters[0].parameter_id); if (!selectedOperation && operations[0]) setSelectedOperation(operations[0].operation_id); }, [snapshot]);
  useEffect(() => { const op = operations.find(item => item.operation_id === selectedOperation); if (!op) return; setMappings(operationParameters.filter(item => item.operation_id === selectedOperation).map(item => ({...item}))); setRules(operationRules.filter(item => item.operation_id === selectedOperation).map(item => ({...item, keywords: {...item.keywords}}))); setSchema(''); const firstBinding = templateBindings.find(row => row.operation_id === selectedOperation); setSelectedTemplatePath(firstBinding?.template_path || ''); setTemplateContent(snapshot?.data.templates?.[firstBinding?.template_path] || ''); setNewVariant(false); }, [snapshot, selectedOperation]);

  const filteredCategories = useMemo(() => categories.filter(item => `${item.category_id} ${item.display_name} ${item.description}`.toLowerCase().includes(search.toLowerCase())), [categories, search]);
  const filteredParameters = useMemo(() => parameters.filter(item => `${item.parameter_id} ${item.display_name} ${item.description} ${item.value_type}`.toLowerCase().includes(search.toLowerCase())), [parameters, search]);
  const filteredOperations = useMemo(() => operations.filter(item => `${item.operation_id} ${item.display_name} ${item.description} ${item.category_id}`.toLowerCase().includes(search.toLowerCase())), [operations, search]);
  const category = categories.find(item => item.category_id === selectedCategory), parameter = parameters.find(item => item.parameter_id === selectedParameter), operation = operations.find(item => item.operation_id === selectedOperation);
  const bindings = templateBindings.filter(item => item.operation_id === selectedOperation);

  function beginCreate(entity: 'category' | 'parameter' | 'operation') {
    setEditorMode(entity);
    setRecord(entity === 'parameter' ? {parameter_id: '', display_name: '', description: '', aliases: [], value_type: 'string', clarification: '', normalizer: ''} : entity === 'operation' ? {operation_id: '', display_name: '', description: '', aliases: [], category_id: selectedCategory || categories[0]?.category_id || '', status: 'inactive'} : {category_id: '', display_name: '', description: '', aliases: [], status: 'active'});
  }
  function beginEdit(entity: 'category' | 'parameter' | 'operation', source: Row) { setEditorMode(entity); setRecord({...source, aliases: [...(source.aliases || [])], __existing: true}); }
  async function saveRecord() {
    const entity = editorMode; if (entity === 'none' || !snapshot) return;
    const idKey = `${entity}_id`, id = record[idKey], existing = Boolean(record.__existing);
    const allowed = entity === 'parameter' ? ['display_name', 'description', 'aliases', 'value_type', 'clarification', 'normalizer', 'cognishield_preset'] : entity === 'category' ? ['display_name', 'description', 'aliases', 'status'] : ['display_name', 'description', 'aliases', 'category_id', 'status'];
    const values = Object.fromEntries(allowed.filter(key => record[key] !== undefined).map(key => [key, record[key]]));
    if (!values.display_name) values.display_name = id;
    if (entity === 'parameter' && !values.normalizer) values.normalizer = null;
    if (await mutate(() => knowledgeApi.edit({expected_revision: snapshot.revision, reason, changes: [{entity, action: existing ? 'update' : 'create', entity_id: id, values}]}), `${titleCase(entity)} draft saved`)) setEditorMode('none');
  }
  function toggleMembership(parameterId: string) {
    if (!snapshot || !category) return; const assigned = categoryParameters.some(item => item.category_id === category.category_id && item.parameter_id === parameterId);
    void mutate(() => knowledgeApi.edit({expected_revision: snapshot.revision, reason, changes: [{entity: 'membership', action: assigned ? 'unassign' : 'assign', values: {category_id: category.category_id, parameter_id: parameterId}}]}), assigned ? 'Parameter removed from category' : 'Parameter assigned to category');
  }
  function saveContract() {
    if (!snapshot || !operation) return; const version = Number(operation.version || 1) + 1; let requiredOrder = 0;
    const rootRule = {operation_id: operation.operation_id, operation_version: version, field_path: '', keywords: {$schema: 'https://json-schema.org/draft/2020-12/schema', type: 'object', additionalProperties: false}};
    const missingRules = mappings.filter(m => !rules.some(r => r.field_path === m.field_path)).map(m => ({field_path:m.field_path, keywords:{}}));
    const populatedRules = [...rules, ...missingRules];
    const contractRules = populatedRules.some(rule => rule.field_path === '') ? populatedRules : [rootRule, ...populatedRules];
    const values = {version, mappings: mappings.map((item, index) => ({...item, operation_id: operation.operation_id, operation_version: version, category_id: operation.category_id, position: index, required_order: item.required ? requiredOrder++ : null})), rules: contractRules.map(item => ({...item, operation_id: operation.operation_id, operation_version: version})), templates: bindings.map(item => {const fields = [...new Set(mappings.map(m => m.field_path.split(/[.\[]/)[0]))]; const required = new Set([...mappings.filter(m => m.required).map(m => m.field_path), ...(contractRules.find(r=>r.field_path==='')?.keywords?.['x-required-by-vendor']?.[item.vendor]||[])]); return {...item, operation_version: version, input_contract:{...item.input_contract,fields,optional_defaults:Object.fromEntries(fields.filter(f=>!required.has(f)).map(f=>[f,null]))}}})};
    void mutate(() => knowledgeApi.edit({expected_revision: snapshot.revision, reason, changes: [{entity: 'contract', action: 'replace', entity_id: operation.operation_id, values}]}), 'Operation contract saved');
  }
  function applyPreset(parameterId: string) {
    const mapping = mappings.find(m=>m.parameter_id===parameterId);
    const preset = parameters.find(p=>p.parameter_id===parameterId)?.cognishield_preset;
    if (!mapping || !preset) return;
    setRules(rows=>[...rows.filter(r=>r.field_path!==mapping.field_path), {field_path:mapping.field_path, keywords:{...(rows.find(r=>r.field_path===mapping.field_path)?.keywords||{}),...preset}}]);
    Toast.success('Preset applied to draft contract', 'Review and save the operation contract to persist these rules.');
  }
  function setKeyword(index: number, keyword: string, value: unknown) { setRules(rows => rows.map((row, current) => { if (current !== index) return row; const keywords = {...row.keywords}; if (value === '') delete keywords[keyword]; else keywords[keyword] = value; return {...row, keywords}; })); }

  if (busy && !snapshot) return <div className="flex h-full items-center justify-center"><span className="loading loading-spinner loading-lg text-primary"/></div>;
  if (!snapshot) return <div className="p-6"><Empty icon={AlertTriangle} title="Knowledge service unavailable" text="Start the backend and refresh this page."/></div>;
  if (!snapshot.data.initialized) return <div className="w-full h-full relative"><button className="btn btn-sm btn-primary absolute right-6 top-6 z-10" onClick={() => setPreview(true)}>Reference-data preview</button><WorkspaceSetup reason={reason} setReason={setReason} busy={busy} role={role} initialize={() => mutate(() => knowledgeApi.initialize(reason), 'Knowledge workspace initialized')}/></div>;

  const actionBar = <div className="ke-actions flex items-end gap-2"><label className="form-control grow"><span className="label-text pb-1 text-xs font-medium">Change reason</span><input className={input} value={reason} onChange={event => setReason(event.target.value)} placeholder="Required when saving or publishing"/></label><button className="btn btn-square btn-sm" title="Refresh" onClick={() => void load(true)} disabled={busy}><RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`}/></button></div>;

  const context = {preview,previewOnly,setPreview,initialPage,snapshot,busy,setBusy,reason,setReason,search,setSearch,
    selectedCategory,setSelectedCategory,selectedParameter,setSelectedParameter,selectedOperation,setSelectedOperation,
    record,setRecord,editorMode,setEditorMode,mappings,setMappings,rules,setRules,schema,setSchema,
    selectedTemplatePath,setSelectedTemplatePath,templateContent,setTemplateContent,newVariant,setNewVariant,variant,setVariant,
    validation,setValidation,role,editable,categories,parameters,operations,categoryParameters,templateBindings,
    operationParameters,operationRules,activeRelease,filteredCategories,filteredParameters,filteredOperations,
    category,parameter,operation,bindings,beginCreate,beginEdit,saveRecord,toggleMembership,saveContract,setKeyword,applyPreset,
    mutate,setView,actionBar};
  return <div className={`ke-workspace ke-${initialPage.toLowerCase()}`}>
    {actionError && <div role="alert" className="alert alert-error whitespace-pre-wrap"><span>{actionError}</span><button className="btn btn-sm btn-ghost" onClick={() => setActionError('')}>Dismiss</button></div>}
    <KnowledgeLayouts c={context}/>
    {editorMode !== 'none' && (initialPage !== 'Parameters' || editorMode !== 'parameter') &&
      <RecordDrawer entity={editorMode} record={record} setRecord={setRecord} categories={categories}
        editable={editable && !preview} busy={busy} onClose={() => setEditorMode('none')} onSave={saveRecord}/>}
  </div>;
}

function WorkspaceSetup({reason, setReason, busy, role, initialize}: any) {
  return <div className="h-full overflow-auto p-6"><div className="mx-auto max-w-4xl space-y-6"><PageHeader icon={Sparkles} title="Knowledge Engineering" description="Create the managed catalog used by V9 interpretation, validation and generation."/><div className={`${card} overflow-hidden`}><div className="grid gap-6 p-6 md:grid-cols-[1fr_320px]"><div><Badge tone="info">One-time setup</Badge><h2 className="mt-3 text-xl font-semibold">Initialize the CogniShield knowledge workspace</h2><p className="mt-2 text-sm leading-6 opacity-70">This imports the verified V9 published baseline into a CogniShield-owned SQLite workspace. The sibling V9 repository stays read-only. Draft changes will not affect Studio until an administrator validates and publishes a release.</p><div className="mt-5 grid gap-3 sm:grid-cols-3">{[[Database, 'SQLite drafts', 'Persistent authoring records'], [ShieldCheck, 'Controlled release', 'Validate before activation'], [GitBranch, 'Read-only baseline', 'No sibling source changes']].map(([Icon, title, text]: any) => <div className="rounded-lg bg-base-200/60 p-3" key={title}><Icon className="h-5 w-5 text-primary"/><div className="mt-2 text-sm font-semibold">{title}</div><div className="text-xs opacity-60">{text}</div></div>)}</div></div><div className="rounded-xl border border-base-300 bg-base-200/50 p-4"><label className="form-control"><span className="label-text mb-2 font-medium">Initialization reason</span><textarea className="textarea textarea-bordered min-h-28 bg-base-100" value={reason} onChange={event => setReason(event.target.value)} placeholder="e.g. Initialize local V9 knowledge workspace"/></label><button className="btn btn-primary mt-4 w-full" disabled={busy || role !== 'admin' || !reason.trim()} onClick={initialize}><Database className="h-4 w-4"/>Initialize workspace</button>{role !== 'admin' && <p className="mt-2 text-xs text-warning">Administrator access is required for initialization.</p>}</div></div></div></div></div>;
}

function RecordDrawer({entity, record, setRecord, categories, editable, busy, onClose, onSave}: {entity: 'category' | 'parameter' | 'operation'; record: Row; setRecord: React.Dispatch<React.SetStateAction<Row>>; categories: Row[]; editable: boolean; busy: boolean; onClose: () => void; onSave: () => void}) {
  const idKey = `${entity}_id`, existing = Boolean(record.__existing);
  return <div className="ke-drawer-overlay" onMouseDown={event => event.target === event.currentTarget && onClose()}><aside role="dialog" aria-modal="true" aria-label={`${existing ? 'Edit' : 'Create'} ${entity}`} className="ke-drawer border-l border-base-300 bg-base-100 shadow-2xl"><div className="sticky top-0 z-10 flex items-center justify-between border-b border-base-300 bg-base-100 px-5 py-4"><div><h2 className="text-lg font-bold">{existing ? 'Edit' : 'Create'} {entity}</h2><p className="text-xs opacity-50">Saved to the SQLite authoring draft</p></div><button className="btn btn-circle btn-ghost btn-sm" onClick={onClose}><X className="h-4 w-4"/></button></div><div className="ke-scroll space-y-4 p-5"><label className="form-control"><span className="label-text mb-1 font-medium">Machine ID <span className="text-error">*</span></span><input className={input} disabled={existing} value={record[idKey] || ''} onChange={event => setRecord(value => ({...value, [idKey]: event.target.value}))}/><span className="mt-1 text-xs opacity-45">Lowercase letters, numbers and underscores</span></label><label className="form-control"><span className="label-text mb-1 font-medium">Display name <span className="text-error">*</span></span><input className={input} value={record.display_name || ''} onChange={event => setRecord(value => ({...value, display_name: event.target.value}))}/></label>{entity === 'operation' && <label className="form-control"><span className="label-text mb-1 font-medium">Category</span><select className={select} value={record.category_id || ''} onChange={event => setRecord(value => ({...value, category_id: event.target.value}))}>{categories.map(category => <option key={category.category_id} value={category.category_id}>{category.display_name || category.category_id}</option>)}</select></label>}{entity === 'parameter' && <label className="form-control"><span className="label-text mb-1 font-medium">Data type</span><select className={select} value={record.value_type || 'string'} onChange={event => setRecord(value => ({...value, value_type: event.target.value}))}>{['string','integer','number','boolean','array','object','null'].map(type => <option key={type}>{type}</option>)}</select></label>}<label className="form-control"><span className="label-text mb-1 font-medium">Description</span><textarea className="textarea textarea-bordered min-h-24 bg-base-100" value={record.description || ''} onChange={event => setRecord(value => ({...value, description: event.target.value}))}/></label><label className="form-control"><span className="label-text mb-1 font-medium">Aliases</span><input className={input} value={(record.aliases || []).join(', ')} onChange={event => setRecord(value => ({...value, aliases: split(event.target.value)}))}/><span className="mt-1 text-xs opacity-45">Comma separated phrases used during interpretation</span></label>{entity === 'parameter' ? <><label className="form-control"><span className="label-text mb-1 font-medium">Clarification question</span><input className={input} value={record.clarification || ''} onChange={event => setRecord(value => ({...value, clarification: event.target.value}))}/></label><label className="form-control"><span className="label-text mb-1 font-medium">Normalizer</span><input className={input} value={record.normalizer || ''} onChange={event => setRecord(value => ({...value, normalizer: event.target.value}))}/></label></> : <label className="form-control"><span className="label-text mb-1 font-medium">Status</span><select className={select} value={record.status || 'inactive'} onChange={event => setRecord(value => ({...value, status: event.target.value}))}><option value="inactive">Inactive</option><option value="active">Active</option></select></label>}</div><div className="sticky bottom-0 flex justify-end gap-2 border-t border-base-300 bg-base-100 p-4"><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy || !editable || !record[idKey] || !record.display_name} onClick={onSave}><Save className="h-4 w-4"/>Save draft</button></div></aside></div>;
}

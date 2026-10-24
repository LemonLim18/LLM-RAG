/** Exact-base Monaco transaction. This mutates buffers only; it never saves. */
export interface WorkspaceChange { path:string;original:string;suggested:string }
/** Restore only a registered open tab, preserving its unsaved text and identity. */
export function openDocumentModel<T extends {isDisposed:()=>boolean}>(path:string,tabs:{path:string;content:string}[],
  existing:(path:string)=>T|null,create:(path:string,content:string)=>T):T|null {
  const model=existing(path);
  if(model && !model.isDisposed())return model;
  const tab=tabs.find(item=>item.path===path);
  return tab?create(path,tab.content):null;
}
interface Model {
  getValue: (eol?:unknown,preserveBOM?:boolean)=>string;
  getFullModelRange: ()=>unknown;
  pushStackElement: ()=>void;
  pushEditOperations: (cursor:unknown[],edits:{range:unknown;text:string}[],compute:()=>null)=>unknown;
}
export function applyWorkspaceChanges(changes:WorkspaceChange[],resolve:(path:string)=>Model|null):void {
  if (!changes.length || new Set(changes.map(c=>c.path)).size!==changes.length) throw Error('Invalid coordinated file set');
  const items=changes.map(change=>{
    const model=resolve(change.path);
    if (!model || model.getValue(undefined,true)!==change.original) throw Error('Stale workspace buffer: '+change.path);
    const eols:string[]=change.suggested.match(/\r\n|\r|\n/g)||[];
    if (new Set(eols).size>1 || eols.includes('\r') || change.suggested.startsWith('\uFEFF')!==change.original.startsWith('\uFEFF')) throw Error('Line-ending/BOM conflict: '+change.path);
    return {change,model};
  });
  const touched:typeof items=[];
  try {
    for (const item of items) {
      touched.push(item);item.model.pushStackElement();
      item.model.pushEditOperations([],[{range:item.model.getFullModelRange(),text:item.change.suggested.replace(/^\uFEFF/,'')}],()=>null);
      item.model.pushStackElement();
      if (item.model.getValue(undefined,true)!==item.change.suggested) throw Error('Monaco refused the exact change: '+item.change.path);
    }
  } catch (error) {
    const failures:string[]=[];
    for (const item of touched.reverse()) {
      try {
        if (item.model.getValue(undefined,true)!==item.change.original) {
          item.model.pushEditOperations([],[{range:item.model.getFullModelRange(),text:item.change.original.replace(/^\uFEFF/,'')}],()=>null);
          item.model.pushStackElement();
        }
        if (item.model.getValue(undefined,true)!==item.change.original) failures.push(item.change.path);
      } catch { failures.push(item.change.path); }
    }
    if (failures.length) throw Error('Partial edit could not be rolled back in: '+failures.join(', ')+'. Review these buffers before continuing.');
    throw Error('Coordinated edit rolled back; original buffers restored. '+String(error));
  }
}

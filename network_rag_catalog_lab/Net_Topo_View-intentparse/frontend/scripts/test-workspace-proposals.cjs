const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const Module=require('node:module');
const ts=require('typescript');
const file=path.join(__dirname,'../src/utils/workspaceProposal.ts');
const compiled=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
const subject=new Module(file,module);subject.filename=file;subject.paths=module.paths;subject._compile(compiled,file);
const {applyWorkspaceChanges,openDocumentModel}=subject.exports;
function model(value,fail=false){return {value,fail,getValue(){return this.value;},getFullModelRange(){return {};},pushStackElement(){},pushEditOperations(_,edits){if(this.fail){this.fail=false;throw Error('injected model failure');}this.value=edits[0].text;}};}

test('restored inactive open tab materializes its unsaved buffer rather than a saved file',()=>{
 const tabs=[{path:'playbooks/vars.yml',content:'neighbor_ip: unsaved\n'}];let calls=0;
 const created=openDocumentModel(tabs[0].path,tabs,()=>null,(path,content)=>{calls++;return {path,content,isDisposed:()=>false};});
 assert.equal(created.content,tabs[0].content);assert.equal(calls,1);
 const live={content:'newer Monaco text',isDisposed:()=>false};
 assert.equal(openDocumentModel(tabs[0].path,tabs,()=>live,()=>{throw Error('must not replace live model');}),live);
 assert.equal(openDocumentModel('not-open.yml',tabs,()=>null,()=>{throw Error('must not read arbitrary path');}),null);
});
test('atomic two-file acceptance preserves all unmodified text and can be undone exactly',()=>{
 const a=model('# keep\nneighbor: old\n'),b=model('reference: neighbor\n# original\n');
 const changes=[{path:'a',original:a.value,suggested:'# keep\nneighbor: new\n'},{path:'b',original:b.value,suggested:'reference: neighbor\n# reviewed\n'}];
 const resolve=p=>p==='a'?a:b;
 applyWorkspaceChanges(changes,resolve);assert.equal(a.value,changes[0].suggested);assert.equal(b.value,changes[1].suggested);
 applyWorkspaceChanges(changes.map(c=>({...c,original:c.suggested,suggested:c.original})),resolve);
 assert.equal(a.value,changes[0].original);assert.equal(b.value,changes[1].original);
});
test('second stale base prevents every file change',()=>{
 const a=model('a'),b=model('concurrent edit');
 assert.throws(()=>applyWorkspaceChanges([{path:'a',original:'a',suggested:'A'},{path:'b',original:'b',suggested:'B'}],p=>p==='a'?a:b),/Stale/);
 assert.equal(a.value,'a');assert.equal(b.value,'concurrent edit');
});
test('failure applying the second file rolls the first back exactly',()=>{
 const a=model('a'),b=model('b',true);
 assert.throws(()=>applyWorkspaceChanges([{path:'a',original:'a',suggested:'A'},{path:'b',original:'b',suggested:'B'}],p=>p==='a'?a:b),/original buffers restored/);
 assert.equal(a.value,'a');assert.equal(b.value,'b');
});
test('mixed line endings, BOM changes and duplicate paths are rejected before application',()=>{
 for(const change of [{path:'a',original:'a',suggested:'A\r\nB\n'},{path:'a',original:'a',suggested:'\uFEFFA'}]){
  const a=model('a');assert.throws(()=>applyWorkspaceChanges([change],()=>a),/BOM/);assert.equal(a.value,'a');
 }
 const a=model('a');assert.throws(()=>applyWorkspaceChanges([{path:'a',original:'a',suggested:'A'},{path:'a',original:'a',suggested:'B'}],()=>a),/Invalid/);
});

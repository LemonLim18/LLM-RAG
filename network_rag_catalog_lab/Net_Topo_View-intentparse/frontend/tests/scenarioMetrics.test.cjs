const {test}=require('node:test');
const assert=require('node:assert/strict');
const ts=require('typescript');
const fs=require('node:fs');
const vm=require('node:vm');
const filename=require('node:path').join(__dirname,'../src/utils/scenarioMetrics.ts');
const output=ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const context={exports:{}};vm.runInNewContext(output,context);
const {metricPreview}=context.exports;
const record={values:{samples:[{timestamp:'2026-10-18T00:59:00Z',value:4},{timestamp:'2026-10-18T00:59:30Z',value:null},{timestamp:'2026-10-18T01:00:00Z',value:8}]}};

test('UTC preview uses actual window samples and retains missing values',()=>{
  const result=metricPreview(record,'2026-10-18T00:58:59','2026-10-18T00:59:31');
  assert.equal(result.error,'');assert.equal(result.points.length,2);assert.equal(result.points[1].value,null);
  assert.equal(record.values.samples.length,3);
  const explicit=metricPreview(record,'2026-10-18T00:58:59Z','2026-10-18T00:59:31Z');
  assert.equal(explicit.error,'');assert.equal(explicit.points.length,2);
});
test('invalid draft points and windows are disclosed instead of drawing invented values',()=>{
  for(const points of [[null],[7],[{timestamp:'2026-10-18T00:59:00',value:1}],[{timestamp:'2026-10-18T00:59:00Z',value:Infinity}],[...record.values.samples].reverse()])
    assert.notEqual(metricPreview({values:{samples:points}}).error,'');
  assert.notEqual(metricPreview(record,'2026-10-19T00:00','2026-10-18T00:00').error,'');
  assert.equal(metricPreview({values:{value:8}}).points.length,0);
  assert.notEqual(metricPreview({values:{unit:'percent',samples:[{timestamp:'2026-10-18T00:59:00Z',value:101}]}}).error,'');
});

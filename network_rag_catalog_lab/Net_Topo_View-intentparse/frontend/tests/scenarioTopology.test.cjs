const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const ts=require('typescript');
const compiled=ts.transpileModule(fs.readFileSync(__dirname+'/../src/utils/scenarioTopology.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const context={exports:{}};vm.runInNewContext(compiled,context);
const {topologyEndpoints,topologyEndpointLabel,rebindTopologyEndpoint}=context.exports;
const inventory={devices:[{id:1,hostname:'A'},{id:2,hostname:'B'},{id:3,hostname:'C'}],
  interfaces:[{id:11,device_id:1,name:'Port1'},{id:21,device_id:2,name:'Port1'},{id:31,device_id:3,name:'Port3'}]};
test('observed endpoints override a plan hint without rewriting either source',()=>{
  const planned=[{id:8,src_device_id:1,src_interface_id:11,dst_device_id:2,dst_interface_id:21}];
  const observed={values:{link_id:8,endpoints:{src_device_id:1,src_interface_id:11,dst_device_id:3,dst_interface_id:31}}};
  const ends=topologyEndpoints(observed,planned);
  assert.equal(topologyEndpointLabel(ends,'dst',inventory).device,'C');
  assert.equal(topologyEndpointLabel(ends,'dst',inventory).port,'Port3');
  ends.dst_device_id=2;assert.equal(observed.values.endpoints.dst_device_id,3);assert.equal(planned[0].dst_device_id,2);
  assert.equal(topologyEndpoints({values:{link_id:8}},planned).dst_device_id,2);
});
test('changing devices clears an incompatible interface instead of guessing by its name',()=>{
  const ends={src_device_id:1,src_interface_id:11,dst_device_id:3,dst_interface_id:31};
  const rebound=rebindTopologyEndpoint(ends,'src','device',2,inventory);
  assert.equal(rebound.src_interface_id,null);assert.equal(ends.src_interface_id,11);
  assert.equal(topologyEndpointLabel(rebound,'src',inventory).valid,false);
  assert.equal(rebindTopologyEndpoint(rebound,'src','interface',21,inventory).src_interface_id,21);
  assert.equal(rebindTopologyEndpoint(rebound,'src','interface',31,inventory).src_interface_id,null);
});

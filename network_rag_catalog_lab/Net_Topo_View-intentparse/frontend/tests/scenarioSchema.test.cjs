const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const ts=require('typescript');
const compiled=ts.transpileModule(fs.readFileSync(__dirname+'/../src/utils/scenarioSchema.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const context={exports:{}};vm.runInNewContext(compiled,context);
const {fieldDefault,fieldSchema,canAddField}=context.exports;
test('first record exposes required fields without inventing network values',()=>{
  const record={type:'object',required:['id','device_id','timestamp','kind'],additionalProperties:false,properties:{
    id:{type:'string'},device_id:{type:'integer',minimum:1},timestamp:{type:'string',format:'date-time'},kind:{type:'string'},values:{type:'object',default:{},additionalProperties:true}}};
  const value=fieldDefault(record);
  assert.deepEqual(JSON.parse(JSON.stringify(value)),{id:'',device_id:1,timestamp:'',kind:'',values:{}});
  assert.equal(canAddField('command',value,record),false);
});
test('enum, nullable numeric and nested defaults retain their types',()=>{
  assert.equal(fieldDefault({enum:['up','down']}),'up');
  assert.equal(fieldSchema({anyOf:[{type:'integer',minimum:1},{type:'null'}]}).type,'integer');
  assert.equal(fieldDefault({default:null,anyOf:[{type:'integer'},{type:'null'}]}),null);
  const rule={type:'object',default:{samples:[]}};const a=fieldDefault(rule);a.samples.push(7);
  assert.equal(fieldDefault(rule).samples.length,0);
});
test('open record values allow deliberate new fields but reject duplicate and prototype keys',()=>{
  assert.equal(canAddField('physical_collection_performed',{},{}),true);
  for(const key of ['__proto__','constructor','prototype','bad key','metric'])assert.equal(canAddField(key,{metric:1},{}),false);
});

test('structured protocol fields choose the actual discriminator without forcing OSPF onto BGP',()=>{
  const variants=['OSPF','BGP'].map(protocol=>({type:'object',properties:{protocol:{const:protocol},left:{type:'object',properties:{[protocol==='OSPF'?'router_id':'local_as']:{type:protocol==='OSPF'?'string':'integer'}}}},required:['protocol','left']}));
  const schema={type:'object',if:{anyOf:[{required:['left']},{required:['right']}]},then:{oneOf:variants}};
  assert.equal(fieldSchema(schema,{protocol:'BGP',left:{local_as:65001}}).properties.protocol.const,'BGP');
  assert.equal(fieldSchema(schema,{protocol:'OSPF',left:{router_id:'192.0.2.1'}}).properties.protocol.const,'OSPF');
  assert.equal(fieldSchema(schema,{protocol:'OSPF'}).properties,undefined);
  assert.equal(fieldDefault(variants[1]).protocol,'BGP');
});

/** Form scaffolding only. Backend validation remains authoritative. */
export function fieldSchema(schema:any,value?:any):any {
  if (!schema || typeof schema!=='object') return {};
  const choices=schema.oneOf||schema.anyOf;
  const matches=(part:any)=>Object.entries(part.properties||{}).every(([key,rule]:[string,any])=>
    !Object.hasOwn(rule,'const')||value?.[key]===rule.const);
  if(schema.if&&schema.then&&value&&typeof value==='object'&&
    schema.if.anyOf?.some((part:any)=>(part.required||[]).every((key:string)=>Object.hasOwn(value,key)))) {
    return fieldSchema({...schema,...schema.then,if:undefined,then:undefined},value);
  }
  const alternative=choices?.find((part:any)=>part.type!=='null'&&matches(part))||choices?.find((part:any)=>part.type!=='null');
  return alternative?{...schema,...alternative}:schema;
}

export function fieldDefault(schema:any):any {
  if (schema && Object.hasOwn(schema,'default')) return JSON.parse(JSON.stringify(schema.default));
  const rule=fieldSchema(schema);
  if (Object.hasOwn(rule,'const')) return rule.const;
  if (rule.enum?.length) return rule.enum[0];
  if (rule.type==='object' || rule.properties) {
    return Object.fromEntries(Object.entries(rule.properties||{}).filter(([key,part]:[string,any])=>
      (rule.required||[]).includes(key)||Object.hasOwn(part,'default')).map(([key,part])=>[key,fieldDefault(part)]));
  }
  if (rule.type==='array') return [];
  if (rule.type==='boolean') return false;
  if (rule.type==='number'||rule.type==='integer') return rule.minimum??0;
  return '';
}

export function canAddField(name:string,value:any,schema:any):boolean {
  const rule=fieldSchema(schema);
  return rule.additionalProperties!==false && /^[a-zA-Z_][a-zA-Z0-9_.-]{0,79}$/.test(name) &&
    !['__proto__','prototype','constructor'].includes(name) && !Object.hasOwn(value,name);
}

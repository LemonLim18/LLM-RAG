/** Draft projection only; the existing backend validates/activates all records. */
export function topologyEndpoints(record:any,planned:any[]=[]):any {
  if(record?.values?.endpoints)return {...record.values.endpoints};
  const link=record?.values?planned.find(row=>row.id===record.values.link_id):record;
  return link?Object.fromEntries(['src_device_id','src_interface_id','dst_device_id','dst_interface_id'].map(key=>[key,link[key]??null])):{};
}

export function topologyEndpointLabel(ends:any,side:'src'|'dst',inventory:any):{device:string;port:string;valid:boolean} {
  const device=inventory?.devices?.find((row:any)=>row.id===ends[side+'_device_id']);
  const port=inventory?.interfaces?.find((row:any)=>row.id===ends[side+'_interface_id']&&row.device_id===device?.id);
  return {device:device?.hostname??'Unresolved device',port:port?.name??'Choose a recorded interface',valid:!!device&&!!port};
}

export function rebindTopologyEndpoint(ends:any,side:'src'|'dst',field:'device'|'interface',value:number|null,inventory:any):any {
  const next={...ends,[side+'_'+field+'_id']:value};
  const device=next[side+'_device_id'];
  if(!inventory?.interfaces?.some((row:any)=>row.id===next[side+'_interface_id']&&row.device_id===device))next[side+'_interface_id']=null;
  return next;
}

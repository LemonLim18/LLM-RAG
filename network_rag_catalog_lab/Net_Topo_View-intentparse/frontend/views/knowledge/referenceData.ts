// Deliberate screenshot examples, never sent to the knowledge API or SQLite.
export type KnowledgeRow = Record<string, any>;
const parameterRows = [
 ['vlan_name','String','3 - 32 chars|Pattern: [a-zA-Z0-9_-]+','Name of the VLAN',5],
 ['vlan_id','Integer','1 - 4094|Unique per device','VLAN ID in range 1-4094',5],
 ['description','String','0 - 255 chars','Description for the resource',8],
 ['interface_name','String','Pattern: [a-zA-Z0-9/._-]+','Interface name (e.g. Gig0/1, Ethernet1/1)',12],
 ['ip_address','IP Address','Valid IPv4/IPv6|CIDR allowed','IP address or subnet',10],
 ['prefix_length','Integer','0 - 32 (IPv4)|0 - 128 (IPv6)','Subnet prefix length',7],
 ['vrf_name','String','1 - 32 chars','VRF instance name',3],
 ['as_number','Integer','1 - 4294967295','BGP AS number',4],
 ['community','String','Pattern: \\d+:\\d+','BGP community value',6],
 ['admin_state','Enum','Allowed: [up, down]','Administrative state',6],
 ['device_name','String','1 - 64 chars','Target device hostname',15],
 ['platform','Enum','Allowed: [ios, ios-xe,|nx-os, eos, junos]','Network platform',8],
];
export const referenceParameters = parameterRows.map(([id,type,constraints,description,usage]) => ({
 parameter_id:id, display_name:id, value_type:String(type).toLowerCase(), description, constraints, usage, status:'Active',
 aliases:[], clarification:'', normalizer:''
}));
const categoryRows = [
 ['VLAN',4,6,'2025-06-18 14:32'],['OSPF',6,8,'2025-06-17 11:20'],['BGP',8,10,'2025-06-16 09:18'],
 ['Interface IP',5,8,'2025-06-16 15:46'],['ACL',6,7,'2025-06-15 12:33'],['QoS',4,5,'2025-06-15 10:22'],
 ['Static Routing',6,7,'2025-06-14 09:30'],['Multicast',3,4,'2025-06-13 16:20'],['Security',6,9,'2025-06-12 11:05'],
 ['System',5,6,'2025-06-11 14:50'],['Interface',6,8,'2025-06-11 14:12'],['VRF',3,4,'2025-06-09 10:08']
];
export const referenceCategories = categoryRows.map(([name,ops,params,updated])=>({
 category_id:String(name).toLowerCase().replaceAll(' ','_'),display_name:name,operation_count:ops,parameter_count:params,updated_at:updated,
 description:name==='VLAN'?'Layer-2 network segmentation and VLAN lifecycle operations.':'',status:'active',aliases:[],
}));
export const referenceOperations = [
 ['create_vlan','Create a new VLAN','Active'],['rename_vlan','Rename an existing VLAN','Published'],
 ['delete_vlan','Delete a VLAN','Published'],['assign_vlan_to_interface','Assign a VLAN to an interface','Draft'],
].map(([operation_id,description,status])=>({operation_id,display_name:operation_id,description,status,category_id:'vlan',version:1,aliases:[]}));
export const referenceTemplate = `{# Cisco IOS-XE create_vlan template #}
{# Parameters: vlan_id (required), vlan_name (required),
   description (optional), state (optional) #}
{% if state is defined and state == 'absent' %}
  no vlan {{ vlan_id }}
{% else %}
  vlan {{ vlan_id }}
    name {{ vlan_name }}
{% if description is defined and description %}
    description {{ description }}
{% endif %}
{% endif %}`;
export const referenceBindings = [
 ['cisco','iosxe','17.9','Published'],['cisco','iosxe','17.12','Draft'],['cisco','ios','15.7','Draft'],
 ['juniper','junos','23.4','Published'],['juniper','junos','22.4','Draft'],['huawei','vrp','8.x','Draft'],['huawei','vrp','9.x','Draft'],
].map(([vendor,platform,version,status])=>({vendor,platform,versions:[version],status,operation_id:'create_vlan',operation_version:1,
 template_path:`templates/${vendor}/${platform}/${version}/create_vlan.j2`,description:'Jinja2 template for creating VLAN on Cisco IOS-XE 17.9',
 updated_at:'2026-10-12 14:30',updated_by:'admin'}));
export const referenceReleases = [
 ['v1.2.0','Add OSPF and BGP enhancements','Published','2026-10-12 14:30'],
 ['v1.1.0','Add VLAN and Interface operations','Published','2026-09-15 10:20'],
 ['v1.0.0','Initial release (Core operations)','Published','2026-08-01 09:10'],
 ['v1.3.0','Add ACL and QoS operations','Draft','2026-10-15 16:45'],
 ['v1.3.0-beta','Testing new parameters','Validation Failed','2026-10-10 09:32'],
].map(([version,description,status,created_at])=>({version,description,status,created_at,actor:'admin'}));
export const referenceHistory = [
 ['Parameter','vlan_id','Created','2 hours ago'],['Operation','Create VLAN','Updated','5 hours ago'],
 ['Category','L2 Network','Created','1 day ago'],['Parameter','description','Updated','1 day ago'],
 ['Operation','Delete VLAN','Updated','2 days ago'],['Category','Security','Created','3 days ago'],
 ['Parameter','interface_name','Created','3 days ago'],['Operation','Configure OSPF','Created','5 days ago'],
].map(([type,name,action,time])=>({type,name,action,created_at:time,actor:'admin',reason:name}));
export const referenceSnapshot = {revision:'reference-preview-only',data:{
 initialized:true, active_release:{release_id:'v1.2.0'},history:referenceHistory,releases:referenceReleases,
 templates:Object.fromEntries(referenceBindings.map(b=>[b.template_path,referenceTemplate])),
 catalogs:{categories:referenceCategories,parameters:[...referenceParameters,
 {parameter_id:'state',display_name:'state',value_type:'enum',description:'present / absent',status:'Active'},
 {parameter_id:'trunk_mode',display_name:'trunk_mode',value_type:'enum',description:'Trunk mode',status:'Active'}],
 operations:referenceOperations,
 category_parameters:['vlan_id','vlan_name','description','state','interface_name','trunk_mode'].map(parameter_id=>({category_id:'vlan',parameter_id})),
 operation_parameters:['vlan_id','vlan_name','description','state'].map((parameter_id,index)=>({operation_id:'create_vlan',operation_version:1,category_id:'vlan',parameter_id,field_path:parameter_id,required:index<2,position:index})),
 operation_rules:[{operation_id:'create_vlan',field_path:'vlan_id',keywords:{minimum:1,maximum:4094}},{operation_id:'create_vlan',field_path:'vlan_name',keywords:{maxLength:32}},{operation_id:'create_vlan',field_path:'description',keywords:{maxLength:128}},{operation_id:'create_vlan',field_path:'state',keywords:{enum:['active','suspend']}}],
 template_bindings:referenceBindings,
 }}};

// Newer mockups use a different catalog. Both sets are isolated visual examples.
const latestCategories=[['VLAN','VLAN configuration and management',6,3,'Mar 15, 2024 10:24'],['OSPF','OSPF routing protocol configuration',8,5,'Mar 14, 2024 16:20'],['BGP','BGP routing protocol configuration',10,6,'Mar 12, 2024 14:10'],['QoS','Quality of Service configuration',7,4,'Mar 10, 2024 11:45'],['Interface','Interface configuration and management',6,4,'Mar 08, 2024 09:30'],['ACL','Access Control List configuration',8,5,'Mar 05, 2024 15:12']].map(([n,d,p,o,t])=>({category_id:String(n).toLowerCase(),display_name:String(n),description:String(d),parameter_count:p,operation_count:o,updated_at:t,status:'active',aliases:[]}));
const latestParameterRows=[['vlan_id','integer','Cisco','VLAN ID (1-4094)',12],['vlan_name','string','Cisco','VLAN name (1-32 char)',8],['description','string','All','VLAN description',10],['state','string','All','VLAN state (active/shutdown)',6],['mtu','integer','All','Optional MTU value',4],['interface_list','array','All','Trunk access interfaces',7],['ip_address','string','Juniper','IP address (IPv4)',9],['prefix_length','integer','Juniper','Network prefix length',6],['vrf_name','string','Juniper','VRF name',5],['asn','integer','All','BGP Autonomous System Number',4]];
const otherParameterNames=['area_id','router_id','network','wildcard_mask','neighbor_ip','remote_as','community','route_map','metric','distance','acl_name','sequence','source_address','destination_address','protocol','source_port','destination_port','interface_name','admin_state','speed','duplex','native_vlan','allowed_vlans','policy_name','bandwidth','priority','device_name','enabled'];
const latestParameters=[...latestParameterRows,...otherParameterNames.map(n=>[n,'string','All',n.replaceAll('_',' '),0])].map(([id,type,vendor,description,usage])=>({parameter_id:String(id),display_name:String(id),value_type:String(type),vendor,description,usage,status:'Active',aliases:[],clarification:'',normalizer:''}));
const latestBindings=[['cisco','iosxe','17.9','Mar 14, 2024 16:20'],['cisco','iosxe','17.6','Mar 08, 2024 09:30'],['cisco','nxos','9.3','Mar 06, 2024 15:12'],['juniper','junos','22.4R1','Feb 28, 2024 11:45']].map(([vendor,platform,version,t])=>({vendor,platform,versions:[version],operation_id:'create_vlan',operation_version:1,template_path:`templates/${vendor}/${platform}/${version}/create_vlan.j2`,updated_at:t,updated_by:'admin',status:'Published'}));
const latestOperationTemplate=`{% if state == 'present' %}
  vlan {{ vlan_id }}
  {% if vlan_name %}
    name {{ vlan_name }}
  {% endif %}
  {% if mtu %}
    mtu {{ mtu }}
  {% endif %}
  {% if state_value %}
    state {{ state_value }}
  {% endif %}
  {% if interface_list %}
    {% for intf in interface_list %}
      interface {{ intf }}
    {% endfor %}
  {% endif %}
{% elif state == 'absent' %}
  no vlan {{ vlan_id }}
{% endif %}`;
export const latestReferenceSnapshot={revision:'latest-reference-preview-only',data:{...referenceSnapshot.data,
 active_release:{release_id:'ke-2026.10.1-r3',version:'2026.10.1-r3'},
 templates:Object.fromEntries(latestBindings.map(b=>[b.template_path,latestOperationTemplate])),
 catalogs:{...referenceSnapshot.data.catalogs,categories:latestCategories,parameters:latestParameters,
 operations:referenceOperations.slice(0,3).map((r,i)=>({...r,description:i===0?'Create a VLAN with optional name and configuration settings.':r.description,updated_at:['Mar 14, 2024 16:20','Mar 14, 2024','Mar 12, 2024'][i],updated_by:'admin'})),
 category_parameters:['vlan_id','vlan_name','description','state','mtu','interface_list'].map(parameter_id=>({category_id:'vlan',parameter_id})),
 operation_parameters:['vlan_id','vlan_name','description','state','mtu','interface_list'].map((parameter_id,i)=>({operation_id:'create_vlan',operation_version:1,category_id:'vlan',parameter_id,field_path:parameter_id,required:i===0||i===3,position:i})),template_bindings:latestBindings}}};


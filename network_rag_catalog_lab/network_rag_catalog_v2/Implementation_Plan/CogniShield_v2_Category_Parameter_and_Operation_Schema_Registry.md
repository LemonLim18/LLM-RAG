# CogniShield v2 Category Parameter and Operation Schema Definition

## Purpose

This document defines the initial parameter model for CogniShield v2.

The design separates:

1.  Category Shared Parameter Standard
    -   Defines parameters available within a domain.
    -   Does not define required/optional.
2.  Operation-Specific Schema
    -   Selects parameters from the category.
    -   Defines required/optional usage.

------------------------------------------------------------------------

# VLAN Domain

## Shared Parameters

  Parameter             Type
  --------------------- ---------
  vlan_id               integer
  vlan_name             string
  description           string
  status                enum
  interface             string
  interfaces            list
  allowed_vlans         list
  native_vlan           integer
  translation_vlan_id   integer
  isolation_mode        enum
  voice_vlan            integer

## Operations

  -------------------------------------------------------------------------------
  Operation                       Required Parameters     Optional Parameters
  ------------------------------- ----------------------- -----------------------
  create_vlan                     vlan_id                 vlan_name, description

  modify_vlan                     vlan_id                 vlan_name, description,
                                                          status

  rename_vlan                     vlan_id, vlan_name      description

  delete_vlan                     vlan_id                 vlan_name

  enable_vlan                     vlan_id                 vlan_name

  disable_vlan                    vlan_id                 vlan_name

  assign_vlan_to_access_port      interface, vlan_id      description

  remove_vlan_from_access_port    interface, vlan_id      none

  assign_vlan_to_trunk_port       interface,              native_vlan
                                  allowed_vlans           

  remove_vlan_from_trunk_port     interface,              none
                                  allowed_vlans           

  configure_trunk_allowed_vlans   interface,              none
                                  allowed_vlans           

  set_native_vlan                 interface, native_vlan  none

  configure_vlan_membership       interface, vlan_id      mode

  configure_vlan_translation      vlan_id,                interface
                                  translation_vlan_id     

  configure_vlan_isolation        vlan_id                 isolation_mode

  configure_private_vlan          vlan_id                 isolation_mode

  configure_voice_vlan            vlan_id, voice_vlan     interface
  -------------------------------------------------------------------------------

------------------------------------------------------------------------

# Interface Domain

## Shared Parameters

  Parameter           Type
  ------------------- ---------
  interface           string
  interfaces          list
  description         string
  admin_state         enum
  mode                enum
  vlan_id             integer
  allowed_vlans       list
  ip_address          string
  ipv6_address        string
  subnet_mask         string
  mtu                 integer
  speed               string
  member_interfaces   list
  lacp_mode           string

## Operations

  Operation                           Required Parameters                  Optional Parameters
  ----------------------------------- ------------------------------------ -------------------------
  create_interface_configuration      interface                            description, mode
  modify_interface_configuration      interface                            description, mtu, speed
  remove_interface_configuration      interface                            none
  set_interface_description           interface, description               none
  set_interface_admin_state           interface, admin_state               none
  reset_interface                     interface                            none
  configure_access_port               interface, vlan_id                   description
  configure_trunk_port                interface, allowed_vlans             native_vlan
  set_port_vlan_membership            interface, vlan_id                   mode
  set_trunk_allowed_vlan_list         interface, allowed_vlans             none
  configure_native_vlan               interface, native_vlan               none
  configure_interface_storm_control   interface                            threshold, action
  configure_layer3_interface          interface                            ip_address
  assign_ip_address                   interface, ip_address, subnet_mask   none
  remove_ip_address                   interface                            ip_address
  configure_ipv6_address              interface, ipv6_address              prefix_length
  configure_loopback_interface        interface, ip_address                description
  configure_irb_interface             interface, vlan_id                   ip_address
  create_link_aggregation             interface                            description
  add_member_to_lag                   interface, member_interfaces         none
  remove_member_from_lag              interface, member_interfaces         none
  configure_lacp                      interface, lacp_mode                 none

------------------------------------------------------------------------

# ACL Domain

## Shared Parameters

  Parameter             Type
  --------------------- ------
  acl_name              
  rule_id               
  source_address        
  destination_address   
  protocol              
  action                
  interface             
  direction             
  priority              

## Operations

  ---------------------------------------------------------------------------
  Operation                   Required Parameters     Optional Parameters
  --------------------------- ----------------------- -----------------------
  create_acl                  acl_name                description

  modify_acl                  acl_name                description

  delete_acl                  acl_name                none

  add_acl_rule                acl_name, rule_id,      source_address,
                              action                  destination_address,
                                                      protocol

  modify_acl_rule             acl_name, rule_id       action, conditions

  delete_acl_rule             acl_name, rule_id       none

  reorder_acl_rule            acl_name, rule_id,      none
                              priority                

  apply_acl_to_interface      acl_name, interface,    none
                              direction               

  remove_acl_from_interface   acl_name, interface     direction

  apply_acl_to_zone           acl_name, zone          direction
  ---------------------------------------------------------------------------

------------------------------------------------------------------------

# QoS Domain

## Shared Parameters

  Parameter          Type
  ------------------ ------
  policy_name        
  classifier         
  dscp               
  vlan               
  interface          
  forwarding_class   
  bandwidth          
  rate_limit         
  queue              
  action             

## Operations

  ----------------------------------------------------------------------------------
  Operation                          Required Parameters     Optional Parameters
  ---------------------------------- ----------------------- -----------------------
  create_qos_policy                  policy_name             description

  modify_qos_policy                  policy_name             description

  delete_qos_policy                  policy_name             none

  create_classifier                  classifier              match_conditions

  classify_by_dscp                   dscp                    classifier

  classify_by_vlan                   vlan                    classifier

  classify_by_interface              interface               classifier

  assign_forwarding_class            forwarding_class        queue

  configure_scheduler                scheduler, bandwidth    priority

  configure_shaping                  interface, rate_limit   burst_size

  configure_policing                 interface, rate_limit   action

  mark_dscp                          dscp, action            classifier

  apply_qos_policy_to_interface      policy_name, interface  direction

  remove_qos_policy_from_interface   policy_name, interface  direction
  ----------------------------------------------------------------------------------

------------------------------------------------------------------------

# Static Routing Domain

## Shared Parameters

  Parameter            Type
  -------------------- ------
  destination_prefix   
  next_hop             
  route_preference     
  interface            
  metric               

## Operations

  ----------------------------------------------------------------------------
  Operation                    Required Parameters     Optional Parameters
  ---------------------------- ----------------------- -----------------------
  add_static_route             destination_prefix,     route_preference
                               next_hop                

  modify_static_route          destination_prefix      next_hop,
                                                       route_preference

  delete_static_route          destination_prefix      none

  add_default_route            next_hop                route_preference

  add_floating_static_route    destination_prefix,     metric
                               next_hop,               
                               route_preference        

  configure_route_preference   destination_prefix,     none
                               route_preference        

  configure_next_hop           destination_prefix,     none
                               next_hop                
  ----------------------------------------------------------------------------

------------------------------------------------------------------------

# OSPF Domain

## Shared Parameters

  Parameter               Type
  ----------------------- ------
  router_id               
  process_id              
  area_id                 
  interface               
  network                 
  passive                 
  redistribution_source   

## Operations

  ---------------------------------------------------------------------------------
  Operation                         Required Parameters     Optional Parameters
  --------------------------------- ----------------------- -----------------------
  enable_ospf_process               process_id              router_id

  disable_ospf_process              process_id              none

  set_ospf_router_id                router_id               process_id

  create_ospf_area                  area_id                 process_id

  assign_interface_to_ospf_area     interface, area_id      process_id

  remove_interface_from_ospf_area   interface, area_id      process_id

  configure_passive_interface       interface               area_id

  advertise_network                 network, area_id        process_id

  remove_advertised_network         network, area_id        process_id

  configure_ospf_redistribution     redistribution_source   process_id, metric

  remove_ospf_redistribution        redistribution_source   process_id
  ---------------------------------------------------------------------------------

------------------------------------------------------------------------

## Implementation Intent

This structure should become the foundation for:

Category Management → Shared Parameter Registry → Operation Definition →
Operation Schema Generation → Template Rendering → Future GUI
Integration

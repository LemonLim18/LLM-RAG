# Implementation Plan: Context-Aware Network Intent Resolution Framework

## Version

**Version:** 2.0 Proposed Revision\
**Status:** Design Proposal

------------------------------------------------------------------------

# 1. Objective and Scope

This implementation extends the existing V2 network automation core to
allow a weak local LLM to interpret human network requests while
deterministic components guarantee correctness.

The system must:

-   identify multiple operations inside a single user request
-   associate each operation with the correct target device(s)
-   extract schema-defined parameters
-   detect missing, incomplete, ambiguous, conflicting, or invalid
    information
-   recover information from authoritative planned network context where
    possible
-   ask structured clarification questions when recovery is impossible
-   validate all information before generating vendor-specific
    configuration

The LLM is responsible for interpretation and candidate generation.

Deterministic systems remain responsible for validation, inventory
alignment, schema compliance, and execution safety.

------------------------------------------------------------------------

# 2. Design Philosophy

The system must not trust raw LLM extraction.

The correct flow is:

    Human Prompt
          |
          v
    LLM Understanding
          |
          v
    Candidate Intent / Parameter Extraction
          |
          v
    Deterministic Validation
          |
          v
    Inventory + Planned Context Resolution
          |
          v
    Clarification if Required
          |
          v
    Validated Intent Model
          |
          v
    Schema Validation
          |
          v
    Jinja2 Rendering

------------------------------------------------------------------------

# 3. Existing System Capability

The existing system already provides:

## Intent Understanding

-   operation identification
-   catalog-based operation selection
-   schema-driven extraction

## Inventory Awareness

-   device attributes
-   aliases
-   device validation
-   conflict detection

## Parameter Handling

-   schema validation
-   type checking
-   IP validation
-   inventory alignment

## Rendering

-   vendor-specific Jinja2 templates

------------------------------------------------------------------------

# 4. Existing Limitations

## 4.1 Device Understanding Limitation

Current systems often depend on literal extraction.

Example:

User:

    Configure the backup firewall router in Singapore

The system should not directly extract:

    device = FW01

Instead it should extract:

    device characteristics:

    location = Singapore
    role = backup firewall router

Then inventory resolution determines the actual device.

------------------------------------------------------------------------

## 4.2 Parameter Recovery Limitation

Missing parameters should not immediately become user questions.

The system should first check:

-   inventory
-   planned assignments
-   network context
-   operation-specific data

Only unresolved values should require user input.

------------------------------------------------------------------------

# 5. Target Architecture

                        User Prompt
                             |
                             v

                  Multi Intent Planner

                             |
                             v

                      Intent Graph

                             |
              +--------------+--------------+
              |                             |
              v                             v

     Device Semantic Resolver       Parameter Resolver

              |                             |
              |                             |
     Inventory Context             Schema + Planned Context

              +-------------+---------------+

                            |
                            v

                 Anomaly Resolution Engine

                            |
                 +----------+----------+
                 |                     |
              Resolved             Clarification

                            |
                            v

                  Validation Pipeline

                            |
                            v

                   Vendor Rendering

------------------------------------------------------------------------

# 6. Intent Graph Model

A prompt may contain multiple independent operations.

Example:

    Configure IP on Router1
    Enable BGP on Router2
    Configure VLAN on Switch1

The system creates:

    Intent A
     |
     Device 1
     |
     Parameters


    Intent B
     |
     Device 2
     |
     Parameters


    Intent C
     |
     Device 3
     |
     Parameters

Each operation maintains independent:

-   device binding
-   parameters
-   validation state
-   clarification state

Values must not leak between operations.

------------------------------------------------------------------------

# 7. Device Semantic Resolution Engine

This is the major enhancement.

The system resolves devices using human-like characteristics.

## Step 1: Extract Device Description

LLM extracts:

``` json
{
"location":"Singapore",
"role":"backup firewall",
"type":"router"
}
```

The LLM does not decide the final device.

------------------------------------------------------------------------

## Step 2: Search Inventory

Inventory fields:

-   hostname
-   aliases
-   site
-   role
-   vendor
-   platform
-   tags
-   capabilities

------------------------------------------------------------------------

## Step 3: Candidate Ranking

Example:

    Candidate:

    SG-FW02

    Reason:

    Location match: Singapore
    Role match: backup firewall
    Platform match: firewall router

    Confidence: 95%

------------------------------------------------------------------------

## Decision Rules

High confidence:

    Automatically select

Medium confidence:

    Present options

Low confidence:

    Ask user

------------------------------------------------------------------------

# 8. Operation-to-Device Binding

The system must explicitly represent relationships.

Examples:

    A, B, C on Device 1 and Device 2

    A -> {Device1, Device2}
    B -> {Device1, Device2}
    C -> {Device1, Device2}

Example:

    A and B on Device1
    C on Device2

    A -> {Device1}
    B -> {Device1}
    C -> {Device2}

------------------------------------------------------------------------

# 9. Parameter Resolution Pipeline

Every parameter has:

    Candidate Value
    Source
    Evidence
    Validation Status

Possible states:

    FOUND
    CONFIDENT
    AMBIGUOUS
    MISSING
    INVALID
    CONFLICT

------------------------------------------------------------------------

# 10. Planned Context Resolver

Before asking the user:

Search:

-   inventory
-   planned parameter database
-   network design context

Example:

Missing:

    OSPF area

Context contains:

    Router1 -> OSPF Area 0

System asks:

    Found planned value:

    OSPF Area:
    [0]

    Confirm?

------------------------------------------------------------------------

# 11. Clarification Engine

Questions must be structured objects.

Example:

    Question ID:
    Q001

    Task:
    configure_interface_ip

    Parameter:
    interface

    Issue:
    missing

Display:

    Which interface should be configured?

    1. Ethernet1/1
       User LAN

    2. Ethernet1/2
       Server LAN


    Custom input:
    ____________

The answer is attached only to Q001.

------------------------------------------------------------------------

# 12. Validation Pipeline

All values pass:

    candidate
       |
    field parsing
       |
    normalization
       |
    validation
       |
    state update

Rejected values never enter accepted state.

Validation includes:

-   type checking
-   range checking
-   IP format
-   subnet rules
-   inventory matching
-   platform restrictions

------------------------------------------------------------------------

# 13. Bounded LLM Strategy

LLM stages:

## Stage 1

Planning:

-   identify operations
-   identify possible devices
-   identify relationships

## Stage 2

Extraction:

-   extract schema parameters

## Stage 3

Focused Repair:

Provide:

-   validation errors
-   original evidence
-   available context

Allow one additional attempt.

## Stage 4

Clarification:

If unresolved, ask user.

------------------------------------------------------------------------

# 14. Rendering Pipeline

Rendering only happens after:

-   all intents resolved
-   all devices validated
-   all parameters validated
-   no unresolved questions

Flow:

    Validated Intent Model

            |

    Schema Validation

            |

    Vendor Template Selection

            |

    Jinja2 Rendering

------------------------------------------------------------------------

# 15. Implementation Roadmap

## Phase 1

Fix validation boundary.

## Phase 2

Implement structured clarification framework.

## Phase 3

Implement operation-device binding model.

## Phase 4

Implement Device Semantic Resolution Engine.

## Phase 5

Implement planned-context resolver.

## Phase 6

Improve bounded LLM repair.

## Phase 7

Testing and regression validation.

------------------------------------------------------------------------

# 16. Acceptance Criteria

The system must:

-   correctly separate multiple intents
-   correctly map operations to devices
-   resolve devices using inventory evidence
-   avoid hallucinating devices
-   detect missing parameters
-   recover values from planned context
-   provide selectable options
-   provide custom input
-   validate every user answer
-   prevent invalid data from entering state
-   prevent parameter leakage between tasks
-   prevent rendering before complete validation

The final objective is a network automation assistant that reasons with
human-like context understanding while maintaining deterministic
engineering safety.

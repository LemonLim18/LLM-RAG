# Architecture

```text
USER
 │
 │ "Configure OSPF process 100
 │  and enable OSPF on Gi0/0
 │  in area 0 on R1."
 │
 ▼
┌───────────────────────────────┐
│ 1. CATEGORY CLASSIFICATION    │
│                               │
│ Local Qwen                    │
│ chooses one known category    │
└───────────────┬───────────────┘
                │
                ▼
        category = ospf
                │
                ▼
┌───────────────────────────────┐
│ 2. OPERATION RETRIEVAL        │
│                               │
│ Nomic embedding → ChromaDB    │
│ metadata filter: category     │
│ semantic top-k candidates     │
└───────────────┬───────────────┘
                │
                ▼
       configure_ospf
       configure_ospf_area
       configure_ospf_interface
                │
                ▼
┌───────────────────────────────┐
│ 3. OPERATION SELECTION        │
│                               │
│ Qwen chooses ONLY from        │
│ retrieved candidates          │
└───────────────┬───────────────┘
                │
                ▼
        configure_ospf
                │
                ▼
┌───────────────────────────────┐
│ 4. SCHEMA RETRIEVAL           │
│                               │
│ Load the complete schema      │
│ from the operation registry   │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 5. PARAMETER EXTRACTION       │
│                               │
│ process_id = 100              │
│ interface = Gi0/0             │
│ area = 0                      │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 6. SCHEMA VALIDATION          │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 7. LOCAL DEVICE INVENTORY     │
│                               │
│ R1 → Cisco IOS-XE             │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 8. DETERMINISTIC TEMPLATE     │
│                               │
│ Cisco + operation_id          │
│        ↓                      │
│ configure_ospf/template.j2    │
└───────────────┬───────────────┘
                │
                ▼
          Jinja2 rendering
                │
                ▼
       Cisco configuration
                │
                ▼
         Ansible playbook
```

**One operation = one Chroma document.** Do not split schema parameters into vector chunks.

**RAG discovers the logical operation; it does not choose the executable vendor template.**

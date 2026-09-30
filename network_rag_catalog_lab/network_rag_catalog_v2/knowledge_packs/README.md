# Reviewed Knowledge Packs

These are inputs to existing knowledge-management services, not a second live
catalog. This workspace has promoted all six packs to SQLite and published them
for generation-only terminal prompting. The source manifests retain their original
review status; publication receipts establish runtime activation.

Read [activation results](../docs/KNOWLEDGE_ACTIVATION_RESULTS.md) and the
[44-operation prompt guide](../docs/PROMPT_TESTING_GUIDE.md).

`python -m app.knowledge.pack_promote` rehearses by default. Its explicit `--apply
--actor NAME --reason TEXT` mode captures a backup, installs reviewed assets,
applies through management services and merges demonstration devices. Publication
remains a separate management action. Do not rerun publication merely to prompt.

Read [completion and limitations](../docs/KNOWLEDGE_EXPANSION_COMPLETION.md).
See [command references and evidence limits](SOURCES.md).

From the V2 directory:

```powershell
& ../../.venv/Scripts/python.exe -m app.knowledge.pack_review --check-cases
```

This creates a temporary SQLite rehearsal and offline release, checks all new
bindings and removes the temporary project. It never activates the workspace.

Each domain has:

- `manifest.json`: candidate scope, supported profile subsets, template hashes.
- `changes.json`: existing Category/Parameter/Operation/Contract service changes.
- `context_rules.json`: code-reviewed policies and resource identities.
- `assets/data/templates/`: standalone vendor/operation templates.
- `cases.json`: labelled prompts, payloads and representative output expectations.

Default order: VLAN, Interface, Static Routing, OSPF, ACL, QoS. Existing membership
is reused; reapplying matching packs is a no-op, conflicting edits are rejected.
QoS reuses the direction definition supplied by ACL, so rehearse ACL before QoS.

`fixtures/devices.json` contains only planned demonstration SW1/SW2/SW3 facts.
Do not copy their capability claims onto real devices without verification.
Device-lab acceptance remains required before using generated configurations on devices.

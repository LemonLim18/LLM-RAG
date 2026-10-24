# Prototype inventory and generated-document separation

Verified 23 October 2026 by reading the user-provided `old-intentparse.zip` directly. No archive source was executed and no inventory, database or Vault secret values were inspected.

The prototype already separates these concerns:

- `backend/ansible/inventory.py:40â€“154` resolves selected hostnames and builds inventory. Lines92â€“112 use Vault variable references for connection credentials. A request must not ask the engineer to repeat registered SSH credentials in generated code.
- `backend/ansible/builder.py:561â€“587` builds a genuine playbook entry point with a `hosts` selector. Lines735â€“755 validate that selector against the resolved targets. Target selection in the prompt does not remove the selector from the resulting Ansible document; the builder supplies it.
- `backend/ansible/reference/ospf/cisco_ios/playbook.yml:3` similarly contains a target-host expression and module tasks, without connection usernames/passwords.
- `backend/ansible/runner.py` passes inventory separately. No runner or network execution was performed in this review.

In the current application, native V9 output contains only the vendor-native configuration. A genuine Ansible variant keeps its target selector, module/platform metadata and operation parameters separate from inventory credentials. Native output must not be labelled a playbook simply because YAML parses.

The open `playbooks/g8_browser_main_20261022.yml` and its `vars_files` reference are explicitly controlled G8 multi-file editing fixtures. The referenced value is a neighbor address, not a credential. They were not produced by the native-generation workflow. They remain unsaved and are retained to preserve acceptance evidence; the active editor was switched to the actual previously reviewed Huawei BGP native draft to make the distinction visible.

The existing optional variant renderer now rejects generated connection-credential variables and connection-user overrides. Registered inventory supplies them. This does not forbid operation-specific account configuration parameters. The resolved `hosts` selector and module/plugin checks remain intact. Seven focused BGP/inventory separation cases pass; the combined48 boundary tests pass. No active variant was published or enabled by this change. Active validated Ansible variants remain0.

Archive SHA256: `1aec133d6126baa2598ce863bc02d87142cc5ddadd6cd20de937095f42cd2913`.

Sanitized exact source excerpts and the archive fingerprint are retained in `tmp/phase-g/iterations/20261023-G7-resume/prototype-inventory-architecture.json`. Actual native-editor browser proof: `native-output-inventory-separation-dom.txt` and `.png` in the same directory. Test failures and corrected release-baseline assertions are retained separately; the old44/78 count was historical and was updated to the preserved47/141 release, without modifying that release.

# Standing prior-experience correspondence audit

This audit was completed before Phase 2C design or execution. Phase 2C inherits, rather than weakens, the accepted boundaries from L7, L2, Genie, EXP010, and Phases 2A through 2B2.

- **L7 identity and evidence:** permission is bound to the saved exact run, task, input hash, attempt, slot, call, executable digest, policy digest, and logical-operation digest. Similar text, aliases, prior output, or an interrupted call cannot authorize a replacement. Raw child streams are persisted before interpretation.
- **L2 separation:** authority, execution, observation, deterministic content checking, delivery, and fresh destination readback remain separate steps. A queue history entry or JSON event stream is not destination proof.
- **Genie authority:** the trusted parent alone owns the queue and event surfaces. The child receives no Genie tool, MCP, token, queue path, registry path, owned-root path, callback, or mutation authority. Child output remains untrusted data.
- **EXP010 discipline:** the pilot is a fresh, finite experiment with exact limits and preserved evidence. It does not enter EXP010, inherit its authority, or claim production validity.
- **Earlier UNKNOWN lessons:** once process/model entry is attempted, uncertainty is terminal with `preserve=true` and `allow_new_invocation=false`. There is no retry, refund, reset, replacement, alternate launcher, or continued polling of a terminal state. A deterministic pre-entry defect may reject only before entry.
- **Phase 2B2 correspondence:** the exact attested Codex executable, empty effective tool/MCP inventory, read-only sandbox, assignment-before-release Windows Job Object path, capability snapshot, and kill-on-close/member-accounting checks are reused without broadening child authority.
- **Independence:** same-host/same-provider execution and deterministic parent review are common-cause evidence, not independent proof.
- **Historical integrity:** no historical run is mutated. Phase 2C uses a new two-task synthetic run and new per-operation ledgers.

The permitted Phase 2C claim is only that one fresh, bounded, two-task local batch completed (or stopped fail-closed) under these controls. It is not a daemon, general sandbox, production deployment, independent verification, or permission for broader mutation.

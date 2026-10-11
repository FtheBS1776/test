# Controlling Genie roadmap amendment — standalone autodrive — 2026-10-11 UTC

This amendment supersedes earlier near-term roadmap language wherever it conflicts. It does not supersede Pass 186 authority, scoped HOLDs, the external-integration policy, or any explicit nonclaim limits.

## Newly completed NONCLAIM milestones

### Fixed-root live-state binding package

Disposition: `ACCEPT_NONCLAIM_LIVE_STATE_BINDING_PACKAGE`.

A Windows local read-only plugin package can bind to the fixed Genie-owned `FOLDERID_LocalAppData/GenieReasoningEngine/state-v1` namespace without fixture fallback, arbitrary model-supplied pathname authority, or a synchronized `PLUGIN_DATA` state copy. Traversal and junction escape attacks fail closed. Actual user live state is not yet installed/provisioned on the user's machine.

### Canonical state provisioner

Disposition: `ACCEPT_NONCLAIM_CANONICAL_STATE_PROVISIONER`.

The future standalone owner has a tested stdlib-only one-time staging/publish primitive for NEW canonical state. It uses fixed `.state-v1.init` -> `state-v1` publication, no replace-existing behavior, preserves abandoned/uncertain state, and distinguishes `PUBLISH_UNKNOWN_PRESERVE` from `PUBLISHED_UNVERIFIED_PRESERVE`. It is not a historical-state importer.

### Minimal standalone owner

Disposition: `ACCEPT_NONCLAIM_MINIMAL_STANDALONE_OWNER`.

A local standalone process can create the first NEW canonical run, read status, and advance exactly one existing Genie controller step. It is transport-neutral and does not depend on the MCP/plugin projection. It contains no provider/model/network execution surface.

### Provider-neutral standalone autodrive

Disposition: `ACCEPT_NONCLAIM_STANDALONE_AUTODRIVE`.

Exact tested head: `b72a5df41a28a6b9faec65d115fdf83cc7c5c846`.
Workflow run/job: `38174048555` / `114572527718`.

The standalone owner now reuses the already accepted finite `session_driver.py` (exact raw SHA-256 `89b0fd1ef48d5460dada5cc59b25072a10ec9b5c7049af25eabbb2d4464bf9d9`) through a provider-neutral bridge. No second orchestration loop was added.

Final Windows regression:

- canonical provisioner: 11/11 PASS;
- minimal standalone owner: 5/5 PASS;
- provider-neutral autodrive: 7/7 PASS;
- static and import-closure gates PASS.

The tested automatic path can take a NEW canonical run through existing worker observation, candidate submission, review, bounded repair, delivery and `STOP / ALL_TASKS_COMPLETE` without a human issuing repeated `advance`/continuation commands between successful actions. A two-attempt REPAIR->ACCEPT path also completed automatically within the existing budget.

Uncertainty remains fail-closed:

- UNKNOWN worker observation, worker exception and token mismatch each consume no replacement invocation on a later drive;
- a process/action-limit boundary after candidate submission does not reconstruct reviewer eligibility; the later drive returns `RECONCILE_REVIEW / NO_SESSION_SUBMISSION` and calls neither worker nor reviewer.

Therefore the original product goal of reducing repeated manual `⏩` is now architecturally demonstrated for bounded in-process injected worker/reviewer capabilities. It is **not yet a usable real-model standalone app**, because no concrete model/provider adapter has been selected or installed.

## Current immediate frontier

**Provider adapter selection and conformance** is now the first unavoidable external-integration decision.

Before implementing a provider-specific adapter:

1. evaluate current hosted and local provider options under the standing cost rule (prefer free/local/already-included; no recurring spend by default);
2. avoid making any one provider part of Genie authority/core semantics;
3. preserve the accepted callable worker/reviewer boundary so providers remain replaceable adapters;
4. explicitly address ambiguous request outcomes: a timeout/connection error after request submission may mean the provider accepted the call, so it must map to existing UNKNOWN/no-retry semantics unless provider-specific evidence proves otherwise;
5. bind provider response/correlation evidence to the original Genie token/request before returning `OBSERVED_ACCEPTED`;
6. keep same-model/shared-provider worker/reviewer ancestry explicit rather than calling it independent verification;
7. pin/test any SDK/protocol dependency and avoid requiring the user to maintain another service/runtime unless the benefit clearly justifies it;
8. do not create API credentials, spend money, or install/connect an external provider without the required explicit user action.

## Product ordering from here

1. **Current:** provider-option research + provider-adapter contract/conformance.
2. **Then:** one concrete optional provider adapter with explicit user-supplied credentials/config where necessary; prove uncertainty/no-retry and exact correlation.
3. **Then:** standalone packaging/UI/start-pause-resume work around the already shared core and canonical state. Provider choice remains replaceable.
4. **Then:** actual user-machine canonical state/application installation.
5. **Then:** actual ChatGPT Desktop plugin installation/connection to that same canonical state, requiring explicit user action.
6. **Later/optional:** remote/web/mobile access, public hosting, A2A, additional providers, stronger currentness witness, historical-state migration.

No main merge, promotion, freeze, paid hosting, provider spend, plugin installation, user-machine state mutation, EXP010 execution, or stronger rollback/currentness claim is authorized by this amendment.

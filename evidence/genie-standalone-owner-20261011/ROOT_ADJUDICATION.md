# Root adjudication — Genie minimal standalone owner

Disposition: **ACCEPT_NONCLAIM_MINIMAL_STANDALONE_OWNER**

Accepted subject: the first local standalone-owner lifecycle surface at exact tested commit `624c89a30cc4d1b1e667267eb0b99022bcedba78`, workflow run `38173656302`, job `114571354490`.

## Accepted narrow conclusions

- The standalone owner is a sibling interface over the existing Genie core, not a second engine and not a consumer of the MCP/plugin projection.
- It exact-byte pins the accepted transport-neutral `run_control.py`, which retains the existing source-binding chain into status/runner/queue/journal/bridge/reused core.
- It adds no model/provider/network execution surface and accepts no filesystem pathname from its caller/CLI.
- It can create the first NEW canonical run by acquiring the accepted canonical-state staging capability, initializing/enqueuing through the existing queue core, writing the fixed registry record, and publishing once through the accepted provisioner.
- Deterministic invalid input is rejected before the one-shot staging namespace is acquired.
- Failures after staging acquisition preserve staging and block recreate; post-publication live-binding/status verification failures preserve final state and report `OWNER_PUBLISHED_UNVERIFIED_PRESERVE`.
- It can read canonical run status through existing `GenieStatusTools` semantics.
- It can advance exactly one existing `GenieRunController` step.
- In the tested one-task run, the first advance returned the existing `INVOKE_WORKER` token/request and reserved exactly one model-call slot while invoking no model.
- A second advance returned `RECONCILE_WORKER` with `allow_new_invocation=false`; the reservation count remained exactly one.
- The local CLI surface is restricted to `create`, `status`, and `advance`, with create input on stdin and no pathname option.

## Test evidence

Final environment: Windows Server 2025 / `windows-2025-vs2026`, exact CPython `3.12.10`.

- `STANDALONE_OWNER_STATIC_BOUNDARY_PASS`
- canonical provisioner regression: 11/11 PASS
- standalone owner lifecycle/adversarial suite: 5/5 PASS
- `STANDALONE_OWNER_CLI_SMOKE_PASS`

## Preserved architecture repair

The first owner version/run (`38173501477`, job `114570893971`, head `4fafc1d3009aec57b4611af13259dcfc0c4d5c14`) was functionally green but used `mcp_consumer.py`/`function_adapter.py` only as a convenient source-pin path to reach `run_control.py`. Internal cross-attack rejected that layering because standalone and plugin should be sibling interfaces over the core, not dependencies of one another.

The repair exact-byte pins `run_control.py` directly (`ecc71b088e5a7e3c0bde33b53a7e850dd769daee5b301f2f116edf956599f2d4`) and CI now fails if the owner source references `mcp_consumer` or `function_adapter`. The final full regression passed.

## Authority / claim limits

This disposition does **not** establish or perform:

- migration/import of the user's existing historical state;
- execution on the user's physical machine;
- creation of additional runs after the first canonical root already exists;
- pause/resume;
- provider/model invocation;
- host observation/candidate callbacks;
- candidate review or autonomous continuation to STOP;
- authenticated remote worker identity;
- rollback/currentness or crash-durability guarantees;
- hostile local-user confinement;
- ChatGPT plugin installation/connection;
- final GUI/installer/production readiness;
- authority promotion, freeze, main merge, or EXP010 execution.

Pass 186 remains inherited controlling. This unit remains NONCLAIM.

## Next frontier

The next legitimate unit is a **provider-neutral execution bridge**. It may consume only an existing bound `INVOKE_WORKER` token/request, invoke one injected provider/worker capability exactly once, and feed the resulting observation/candidate back through the already existing runner callback/journal semantics. Uncertain invocation must never create automatic retry permission.

Before implementation, inspect prior host-return / Work adapter evidence and preserve its lessons. Provider-specific APIs, credentials, billing, and network behavior remain separate later adapters under the standing external-integration and cost gates.

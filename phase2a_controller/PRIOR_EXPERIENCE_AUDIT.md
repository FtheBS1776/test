# Phase 2A prior-experience correspondence audit

Status: completed before selection/inspection of the implementation branch head and before any repository edit.

## Reused invariants

1. **L7 identity and integrity do not create authority.** Exact run/task/input/attempt/content identity is necessary, but an MCP registration, transport success, approval dialog, returned token, or role label cannot prove execution, correctness, independence, promotion, or currentness. See `integration_experiment/PRIOR_EXPERIENCE_AUDIT.md`, `active_runner/REVIEW_PLAN.md`, and `evidence_summary/CORRESPONDENCE.md`.
2. **L2 separates authority, execution, observation, and verification.** A progression call may persist a reservation and emit an action without invoking a model. A worker response would be an observation, not controller acceptance. Phase 2A therefore stops at the returned action/token and exposes no event or review surface.
3. **Paths and stores remain host-authoritative.** `shared_interfaces/PRIOR_CORRESPONDENCE.md` and `run_control/CONTRACT.md` require a trusted alias mapping. Model/tool input is only `{run_name}`; it cannot select queue, root, policy, task, budget, module, callback, or operation paths.
4. **Historical completion is not currentness.** Queue history, hashes, and local receipts do not prove future state, rollback resistance, authenticity, or global atomicity. The pilot records exact post-call local state only and remains NONCLAIM.
5. **UNKNOWN is not retry permission.** A failure after entering `runner.step` can conceal committed state. Preserve the reservation and stores; do not refund, reset, replace, relaunch, or automatically retry. Require `preserve=true` and `allow_new_invocation=false` at the new MCP projection boundary.
6. **Shared roles are common-cause.** This implementation, adversarial review, and tests share agent/host/ancestry. They are exact-source and root-controlled checks, not independent evidence.
7. **Reuse the accepted primitive.** `shared_interfaces/run_control.py` already exposes exactly one `advance_run` operation, calls `runner.step` once, and advertises write/destructive/non-idempotent/closed-world metadata. It remains byte-identical at SHA-256 `ecc71b088e5a7e3c0bde33b53a7e850dd769daee5b301f2f116edf956599f2d4`.
8. **Keep read-only and mutation surfaces separate.** `shared_interfaces/mcp_server.py` and the installed `genie-readonly` package remain exactly two-tool read-only surfaces. Phase 2A uses a distinct stdio server, identity, registry, and state root.
9. **Budgets stay finite and charged.** The synthetic policy is one task, one model-call reservation, and one attempt. A returned `INVOKE_WORKER` token is a bound action record only; Phase 2A does not dispatch it.
10. **External metadata is not authorization.** MCP annotations help a host present safeguards but do not replace Genie's alias registry, source pins, schema validation, or authority boundary.

## Attacked shortcuts and disposition

- Add `advance_run` to `genie-readonly`: **REJECT** — collapses the authority boundary and changes the verified package.
- Accept caller-supplied paths or a generic operation name: **REJECT** — violates L7 concrete-subject binding.
- Reuse an existing historical alias/run: **REJECT** — risks same-ID aliasing and historical mutation.
- Invoke `apply_run_event`, `session_driver`, a worker, or reviewer: **DEFER TO PHASE 2B OR LATER**.
- Convert transport success into semantic success: **REJECT** — domain `REJECT` and `UNKNOWN` remain successful MCP transport results with `isError=false`.
- Retry after UNKNOWN or delete/refund the reservation: **REJECT** — uncertainty remains charged and preserved.
- Add HTTP/public listening for the local pilot: **REJECT** — stdio-only is the minimum compatible surface.

## Exact starting head inspected after this audit

- Selected continuation branch: `origin/nonclaim/genie-desktop-plugin-package-20261011`
- Commit: `3224a6234f5a5eac36413a7ac23d5a7ae6ae93ee`
- Tree: `58c8f61d9cf740943956d02e48f312e39b309aaf`
- Subject: `Record Windows package bit-reproducibility limitation (NONCLAIM)`
- Worktree state at selection: clean
- New branch: `nonclaim/genie-phase-2a-local-mutation-20261012`

The initial long-path checkout attempt failed before branch creation on Windows. A clean short-path clone was made, verified at the same exact commit, configured for long paths, and only then branched. No historical run or repository commit was changed by that failed checkout.

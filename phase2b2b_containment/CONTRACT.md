# Phase 2B2B fixture-containment contract — NONCLAIM

## Accepted boundary

`NoModelProcessTreeContainmentProbe.probe(probe_id)` accepts only one lowercase 64-hex parent-owned probe ID. The immutable parent profile binds the exact host Python, exact direct child Python, exact fixture path and digest, exact `-I -S -B` argv, a fresh non-repository temporary cwd, a rebuilt minimal environment, three pipes, closed file descriptors, no shell, and hidden-window creation.

The probe has no request text, model prompt, Genie run alias, token, queue/root path, registry, callback, event, MCP, provider, or authentication field. It is a verification harness, not a worker launcher.

## Ordering and containment evidence

The parent performs one bounded sequence:

1. Verify the selected runtime support set and fixture bytes.
2. Create an unnamed Windows Job Object.
3. Set and query exactly `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, with neither breakaway flag.
4. Start the trusted fixture once and assign its process handle to the job.
5. Verify membership and exactly one pre-gate job member.
6. Send `RELEASE_AFTER_JOB_ASSIGNMENT` once.
7. Strictly parse one bounded fixture report.
8. Wait for the exact tested four-member tree, retain handles, verify every member belongs to the job, and verify two pinned Python plus two pinned console-host images.
9. Terminate the job once, wait through retained handles, and query zero active members.
10. Wait/reap the direct child, explicitly close its Windows process handle, close the job and retained member handles and pipes, and remove the temporary cwd only if all preceding cleanup is verified. A separate test exercises kill-on-close directly.

The deterministic fixture performs no action before reading the gate other than trusted Python startup and imports. After release it starts one sleeping descendant, reports parent/descendant PIDs as untrusted data, and sleeps. It invokes no model, provider, network, Genie, MCP, callback, or reviewer.

## Result semantics

- Invalid probe ID or invalid immutable profile: deterministic `REJECT` before Job Object/process entry.
- Deterministic Job Object creation/configuration failure before process entry: `REJECT / CONTAINMENT_JOB_CONFIGURATION_FAILED`.
- Once `Popen` is attempted, handled entry, assignment, gate, output, membership, image, termination, wait, or cleanup uncertainty: exactly `UNKNOWN / PROCESS_TREE_CONTAINMENT_OUTCOME_UNKNOWN / preserve=true / allow_new_invocation=false`.
- Exact successful local observation: `VERIFIED / NO_MODEL_FIXTURE_CONTAINMENT_EVIDENCE`, still with `allow_new_invocation=false`, `model_invoked=false`, `complete_runtime_closure=false`, and `hostile_preassignment_containment=false`.

One probe object can attempt process entry at most once. Concurrent calls share the same latch. `TerminateJobObject` is also attempted at most once: if that attempt or its readback is uncertain, cleanup closes the already configured kill-on-close job instead of replaying the termination call. It has no process-entry or termination retry, refund, reset, replacement, or alternate execution branch. After live job members are terminated and the owned job, direct-child process, retained-member, and pipe handles are closed, a bounded retry may remove the now-inert temporary directory; that filesystem-only cleanup cannot spawn, terminate, or re-enter a process. Any uncertainty in the preceding cleanup preserves the directory and returns UNKNOWN rather than asserting inert deletion safety. `SystemExit`, forced host termination, power loss, or OS failure can prevent a domain return; none creates retry permission.

## Explicit limits

The Job Object closes the descendant-control gap only for the exact cooperative fixture and tested Windows configuration after successful assignment. It does not establish hostile pre-assignment containment, general escape resistance, network or filesystem confinement, credential isolation, containerization, remote authenticity, complete runtime closure, rollback resistance, or power-loss durability. The trusted local filesystem can still change concurrently between checks and use. Same-host code, hashes, and tests remain common-cause evidence.

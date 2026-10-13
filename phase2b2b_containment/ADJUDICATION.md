# Phase 2B2B root adjudication — NONCLAIM

Decision: **ACCEPT the fixture-only Windows descendant-containment preflight and stop before live Phase 2B2.**

The accepted implementation adds a minimal standard-library `ctypes` wrapper for exactly the required Windows Job Object operations and a separate deterministic gated process-tree fixture. It does not change any accepted Phase 2B2A source. The real final probe verified assignment-before-release, exact non-breakaway kill-on-close policy, every live job member's process handle and image path, one bounded tree termination, four signaled terminated handles, and fresh zero-active readback.

The observed tree included Windows console hosts in addition to the two Python processes; the implementation responded by pinning and verifying those images instead of silently checking only the two expected PIDs. Direct kill-on-close behavior was exercised separately. Injected failures after process entry remain canonical UNKNOWN, and concurrent calls to one probe object produced exactly one process spawn.

Final adversarial audit exposed and repaired two cleanup defects before acceptance: the temporary cwd could be deleted before the Job Object finished reaping a malformed-report tree, and an uncertain `TerminateJobObject` call could be attempted again from cleanup. Cleanup now closes process resources before bounded directory deletion, latches the first termination attempt, and relies on kill-on-close rather than replay. A final accuracy audit then required explicit closure of the direct child's Windows process handle and a hard gate that preserves the cwd whenever preceding cleanup is uncertain. Ten complete final focused-suite repetitions, including 200 malformed-report and 100 injected-termination cases in aggregate, were clean.

This closes one engineering prerequisite only for the exact cooperative fixture on this exact host. It is not proof against hostile pre-assignment behavior or escape techniques, not a filesystem/network/credential sandbox, and not a complete runtime closure. It provides no worker result, review, callback, content truth, independent provenance, completion, delivery, or future currentness.

All 129 focused/regression tests pass with zero skips. Phase 2A/read-only integrity and raw preserved hashes remain exact. No Codex child, model/provider, authentication, MCP registration, Genie mutation, callback, persistent run, main merge, promotion/freeze, spending, or EXP010 activity occurred.

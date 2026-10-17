# Phase 2B2R test and execution results

- Exact GitHub build run `38972902845`: success at head `72ce3ad36ae8a03e3954df591325ff6fd91f419d`.
- Artifact archive SHA-256 matched GitHub's artifact digest.
- Independently computed `codex.exe` SHA-256 matched the workflow checksum:
  `14c0880a58fdb5ba286e38c731e7363989cef94a66061e4d739bdc3d12a3276b`.
- Focused Phase 2B2 adversarial/contract suite after execution: 29 passed,
  zero failures, zero skips.
- Single no-model preflight: `OBSERVED_ACCEPTED`; zero semantic bytes; zero
  model turns; two live-observed members; one termination; zero active members.

The old 129-test historical host suite was also attempted but is not claimed as
a current regression result: its intentionally pinned runtime-digest and
historical-file-count preconditions reject this later accumulated workspace
before exercising those old launchers. No protected historical files were
modified to make that suite green.

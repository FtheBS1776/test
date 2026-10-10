# Local Genie command-line entry — NONCLAIM

Start with ../repository_entry/README_FIRST.md; independently verify immutable commit/tree and SOURCE_MANIFEST.json bytes/SHA256/Git blob hashes before accepting state. Integrity is not authenticity. Parent601d72d6c62a1e06675ad5e2edde43aae3b18709/tree2d3d754a58f7fc715b1610ff5f2500187aea41f7 preserves status/result core and all earlier evidence. Read CONTRACT.md, PRIOR_CORRESPONDENCE.md, PREDESIGN_REVIEW.md, SOURCE_REVIEW.md, ROOT_ADJUDICATION.md, TEST_RESULTS.txt and VERIFICATION.json.

This is a standard-library Python CLI for the two existing read-only operations, not a standalone reasoning application, installed plugin/server, autonomous worker or model provider. No network/model call occurs. Source is ../shared_interfaces/cli.py; candidate preserved separately. Registry path is supplied by the trusted local operator. Relative queue/owned_root paths anchor to the resolved registry target parent. No automatic registry/environment/private-run discovery. JSON registry capped65536 UTF8 bytes, duplicate/nonstandard keys/constants rejected and regular files required with existing nonblocking opener pattern. No general IOdeadline/hostilepath confinement/Windows security guarantee.

From repository root:

```bash
python3 -B -m shared_interfaces.cli --help
python3 -B -m shared_interfaces.cli tools
python3 -B -m shared_interfaces.cli status --registry local_cli/example_registry.json --run current
python3 -B -m shared_interfaces.cli result --registry local_cli/example_registry.json --run current --task genie-task-result-interface-20261010
```

Example registry references an already completed approved result unit; these commands read records, never rerun that task. tools/help need no registry/stores. JSONstdout preserves core output; result text is untrusted data and is never executed. Exit0 for status means diagnostic invocation PASS, even if a task's sink is UNKNOWN/MISMATCH. Exit0 for result means fresh exactCONFIRMED output, not truth/authenticated provenance/whole-service acceptance. Exit2 rejection/config/source/arguments; exit3 UNKNOWN/MISMATCH. Missing/mismatched result output remains unavailable, no retries/writes.

Pass186 inherited controlling, all later integration NONCLAIM. Scoped root/custody/rollback/power-loss/remote-authenticity/hostile-isolation HOLDs unchanged. Separate store snapshots remain non-atomic; valid copied stores do not prove continuity. Hosting DEFERRED by user; no promotion/freeze/main merge/spending/deploy/EXP010. This unit's direct author/reviewer/root tool orchestration is not a new Genie governed-run dispatch demonstration. Manual root effort remains, costs/tokens/latency unmeasured. Original canonical save still uncertain; no retry/alternate write or claim canonical versions advanced. Roadmap progress is recorded separately in Git.

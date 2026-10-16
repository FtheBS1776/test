# Phase 2B2R contract

- Base lineage: verified Phase 2B2B commit `c147d06b242539cb80da5e8ca115828acfef954b`.
- Exact source: `rust-v0.163.0-alpha.11` at `5425d3e625daa58eea3ad1de27c087eb3b2ffbd3`.
- Build lineage: `72ce3ad36ae8a03e3954df591325ff6fd91f419d`.
- Artifact identity: workflow checksum plus independent local SHA-256 readback.
- Capability policy: canonical `{"allowed_tools":[]}`.
- Execution: one fresh, durably claimed no-model logical operation; one
  preflight process, no semantic stdin, no retry or replacement identity.
- Containment: non-breakaway `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, assignment
  verified before semantic release, eager live identity capture, one bounded
  termination, zero-active fresh readback, and signaled retained handles.
- Authority: existing Codex home may identify authentication storage, but no
  credential value, Genie token/path/root/registry, callback, or mutation tool
  is passed to the child.
- Boundary: stop before the live model turn if this preflight does not produce
  `OBSERVED_ACCEPTED`; never replace an entered operation.

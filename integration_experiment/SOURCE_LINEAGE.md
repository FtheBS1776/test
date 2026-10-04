# Source lineage

The four vendored Pass 219 source files are unchanged copies from the independently checked Pass 219 ZIP (outer SHA-256 `a3378908ffc661231d32db72f2213f20b98b78b5570eba3786db8453ab1df647`). Their per-file hashes must match the following exact values:

| File | SHA-256 |
|---|---|
| `atomic_join.py` | `06fe603a6e23fb921d438dea78171da37520844ceb0d4ec4643e54d9edced9b1` |
| `execution_identity_reference.py` | `5447f0084f222cfd340ed427e5336f3a6a9ebd388b78489cbf4d30fdd9164417` |
| `lifecycle_registry.py` | `7ce3a42d05cf69a0066c59a4cdff196e1fc1f5dba46a29123d9b6c2c95bce367` |
| `stateful_subject.py` | `8ea005246f66fd413f00bad6cf0714e5704c23cc4255881ce659e682ce740131` |

The new file `etcd_lifecycle_adapter.py` is a separate reference implementation for this bounded experiment. `test_integration.py` uses the real Pass 219 Ed25519 envelope and registry reference code. `run_integration_evidence.py` is the evidence wrapper and is part of the executed subject. `WORKFLOW_TEMPLATE.yml` is a template; the actual committed workflow must be captured and independently matched to it during adjudication.

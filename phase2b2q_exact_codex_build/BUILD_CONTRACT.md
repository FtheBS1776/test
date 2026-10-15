# Build contract

- Upstream tag: `rust-v0.163.0-alpha.11`
- Upstream commit: `5425d3e625daa58eea3ad1de27c087eb3b2ffbd3`
- Rust toolchain: `1.95.0`
- Target: `x86_64-pc-windows-msvc`
- Package/binary: `codex-cli` / `codex.exe`
- Build profile: debug (bounded pilot only; no production or performance claim)
- Capability policy: canonical JSON `{"allowed_tools":[]}`
- Workflow permissions: repository contents read-only
- Artifact retention: one day
- Model turns: zero

The artifact must not be used unless the workflow succeeds, the downloaded
binary matches the workflow SHA-256 record, and a fresh no-model parser and Job
Object preflight verifies its exact CLI/event behavior.

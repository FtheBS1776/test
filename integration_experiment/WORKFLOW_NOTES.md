# GitHub execution notes

- Manual-only `workflow_dispatch`; Ubuntu 24.04; no secrets, OIDC, or production credentials.
- The GitHub runner downloads the official etcd 3.6.5 release archive over HTTPS. The wrapper checks the archive SHA-256 and both measured executable SHA-256 values before launching the process.
- Actions are pinned to the exact full commits previously used in the Pass 230 evidence lane. Checkout disables credential persistence; token permissions are `contents: read`.
- The runner captures commit/run/attempt/workflow context, actual server command/version/endpoint, exact source bytes/manifest, raw JSON-gateway exchanges, test output, server logs, and all file digests. The result remains pending independent adjudication.
- The server runs as one loopback member over HTTP with no etcd auth. This is intentionally adequate only for the exact client/Txn implementation observations described in `CONFORMANCE_SCOPE.md`.
- The test subject is distinct from the Pass 230 gate. Do not rename or substitute its evidence as a rerun of Pass 230.
- Upload the evidence artifact even when the test step fails. Missing/partial artifact means INDETERMINATE, not success.

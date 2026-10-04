# GitHub execution notes — TLS/RBAC subject

- Branch-push trigger restricted to `nonclaim/pass219-etcd-tls-rbac-20261004`, plus `workflow_dispatch`; Ubuntu 24.04; no GitHub secrets, OIDC, or production credentials. GitHub requires a manual-dispatch workflow file to exist on the default branch to show its UI button, so the isolated branch push is the execution path and the default branch remains unchanged.
- The GitHub runner downloads the official etcd 3.6.5 release archive over HTTPS. The wrapper checks the archive SHA-256 and both measured executable SHA-256 values before launching the process.
- Actions are pinned to the exact full commits previously used in the Pass 230 evidence lane. Checkout disables credential persistence; token permissions are `contents: read`.
- The runner captures commit/run/attempt/workflow context, actual server command/version/endpoint, exact source bytes/manifest, raw JSON-gateway exchanges, test output, server logs, and all file digests. The result remains pending independent adjudication.
- The server runs as one loopback member over HTTPS with a generated run-only CA and server certificate. V3 auth is configured with run-only random users; one test user has a narrowly bounded namespace role. The gateway bearer token is never placed in argv or durable capture. No client certificate or production credential is used.
- etcd's default simple token is documented as development/testing only; the capture makes no production auth claim. `/health` and `/metrics` are not used as RBAC evidence.
- The test subject is distinct from the Pass 230 gate. Do not rename or substitute its evidence as a rerun of Pass 230.
- Upload the evidence artifact even when the test step fails. Missing/partial artifact means INDETERMINATE, not success.

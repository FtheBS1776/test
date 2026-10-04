# HTTPS + RBAC fixture subject — read first

This directory extends the earlier Pass 219 bounded etcd integration subject with a distinct NONCLAIM HTTPS/RBAC fixture. It is not a new handoff and does not alter the controlling pass.

Before editing or execution, read in order:

1. `TLS_RBAC_PRIOR_EXPERIENCE_AUDIT.md` — required L7, L2, Genie, and EXP-010 correspondence.
2. `TLS_RBAC_INTERNAL_ATTACK.md` — candidate failure and abuse cases.
3. `TLS_RBAC_EXTERNAL_RESEARCH.md` — current official etcd v3.6 documentation.
4. `TLS_RBAC_CROSS_ATTACK.md` — disposition, exact tested boundary, and HOLDs.
5. `CONFORMANCE_SCOPE.md` — allowed claims and exclusions.
6. `TLS_RBAC_RUN_1_COUNTEREVIDENCE.md` — first execution failure and verified artifact details.

The executed workflow is `.github/workflows/pass219-etcd-tls-rbac.yml`, restricted to branch `nonclaim/pass219-etcd-tls-rbac-20261004`. It creates one loopback etcd 3.6.5 process, run-only server TLS credentials, and password-authenticated fixture RBAC. Never place passwords, bearer tokens, CA private key, server private key, or wrong-CA private key into command arguments, durable capture, artifacts, or logs.

Every outcome remains NONCLAIM with Pass 186 controlling. GitHub is an executor and evidence transport, not an authority. Do not promote or freeze. Production provider identity/trust, independent administration, lifecycle authority, Pass 220–222 root-transition source integration, production credential custody, and whole-world rollback remain HOLD/out of scope.

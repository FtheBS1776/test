# Run 37203473079 — retained counterevidence (NONCLAIM)

- Commit: `5fc85c8d51e43339445887ff773d9f65f8be77ef`.
- Event/workflow: `push`, `.github/workflows/pass219-etcd-tls-rbac.yml`.
- State: `INDETERMINATE`; test suite 16/18. Run 1 remained a separate INDETERMINATE capture.
- Artifact: `pass219-etcd-tls-rbac-37203473079-1`, artifact ID `11303349313`.
- GitHub SHA-256 and independent local SHA-256: `90db2689d3c9926ca005a02b7cf062dec445f700500b73276cccabe9260ef041`.
- ZIP CRC: valid; 47 evidence members uploaded. The artifact reports `secret_and_private_key_scan: PASS`.
- HTTPS setup, nested RBAC permission, exact `role/get` readback, bad-CA rejection, wrong-host rejection, plaintext downgrade rejection, missing/invalid token rejection, wrong-password rejection, allowed scoped access, denied neighbor access, and the privileged no-write check all passed.
- Two remaining cases errored because test helper clients were created with `Gateway(ENDPOINT)` defaults instead of the configured TLS context and least-privilege token. Logs show TLS CA verification failure. Neither request reached etcd KV handling, so the intended lifecycle mutation / wrong-cluster cases were not tested in this run.

The targeted repair is recorded in `TLS_RBAC_CROSS_ATTACK.md`; this failed artifact remains unchanged.

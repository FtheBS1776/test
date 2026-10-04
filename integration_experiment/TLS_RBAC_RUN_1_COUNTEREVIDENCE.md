# Run 37203215898 — retained counterevidence (NONCLAIM)

- Commit: `88db161e20b47b1c40155059749e8c112c6e9c98`
- Event/workflow: `push`, `.github/workflows/pass219-etcd-tls-rbac.yml`
- State: `INDETERMINATE`; fixture stopped before auth was enabled or tests ran.
- Artifact: `pass219-etcd-tls-rbac-37203215898-1`, artifact ID `11303542114`.
- GitHub SHA-256 and independent local SHA-256: `7f0182b72ca77dac0941d28553201348a5180564e284db53d68e61616c3ba419`.
- ZIP CRC: valid; 38 members uploaded; local review found no auth credential or private-key bytes in the artifact.
- HTTPS server started with etcd 3.6.5. `/v3/auth/user/add`, `/v3/auth/user/grant`, and `/v3/auth/role/add` returned success; `/v3/auth/role/grant` returned HTTP 400.
- Server log: `auth_role_grant_permission` decoded the role `name`, but no permission, then reported `auth: permission not given`.
- Root cause established against the pinned v3.6.5 `rpc.proto` and `auth.proto`: the JSON request omitted the required nested `perm` message. The first artifact is preserved and remains a failed fixture setup, not a test pass.

The repair candidate is in `TLS_RBAC_CROSS_ATTACK.md`. It must verify the exact permission by role readback before enabling auth.

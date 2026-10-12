# Root adjudication — Desktop host compatibility replacement

Disposition: **ACCEPT_NONCLAIM_REPLACEMENT_CANDIDATE**

Accepted subject: Genie Readonly local Windows plugin v0.1.1 built from tested commit `61bf2da663ea260b0b09f544b7d167d31ec55af3`, workflow run `38194250230`, job `114633333562`.

## Accepted narrow conclusions

- The package retains the portable Agent Plugins root manifest and MCP configuration.
- It adds the currently supported `.codex-plugin/plugin.json` + `.mcp.json` compatibility fallback without adding another Genie engine or tool surface.
- Both representations resolve to the same plugin-relative stdio executable and exactly two read-only tools.
- The original historical `actual` fixture still produces PASS and CONFIRMED behavior.
- Deterministic unrecognized input remains REJECT rather than being blurred into UNKNOWN.
- A separately bound synthetic known-task fixture produces `UNKNOWN / TASK_RESULT_UNAVAILABLE` when result evidence is unavailable.
- The synthetic fixture uses a distinct queue policy run ID and does not alter or reinterpret `actual`.
- Persistent state, partial-state preservation, interrupted-init preservation, untrusted-result labeling, source pins, exact dependency closure, and frozen stdio behavior remain intact under the tested package.
- The uploaded delivery artifact was downloaded and independently re-hashed to the same SHA-256.

## Accepted identities

- Plugin version: `0.1.1`
- Synthetic run ID: `genie-plugin-synthetic-unknown-20261011`
- Seed ID: `host-return-plus-unknown-b6bb873bf6c854f2dbaa`
- EXE SHA-256: `885ffc2b6edc6d884127b7aae6883bb524bdcbbdb6ba1f229da612ccd8526f2d`
- EXE bytes: `22133371`
- ZIP SHA-256: `b94b023f618dc9bfc5952482b46d28e66eb38b778ee892b6d788b612536da706`
- ZIP bytes: `21838028`
- Artifact ID: `11722996512`

## Not established

This adjudication does not establish that the user's physical ChatGPT Desktop host successfully discovers, starts, or registers the replacement plugin. It does not reinterpret the earlier zero-tool observation as either proof of a package defect or proof of host correctness.

It also does not establish production trust, signing/authenticity, remote/web/mobile connectivity, whole-store rollback resistance, root/bootstrap/custody continuity, hostile-worker isolation, model dispatch, autonomous continuation, promotion, freeze, main merge, or EXP010 execution.

## Next boundary

Replacement/update of the installed local plugin on the user's physical Windows system is an external action. After that update, a brand-new local ChatGPT Desktop Work/Codex session must verify exactly:

1. tool registry contains only `get_run_status` and `get_task_result`;
2. `actual` -> PASS;
3. confirmed task -> CONFIRMED with `UNTRUSTED_ACCEPTED_TASK_DATA`;
4. nonexistent run -> REJECT / UNKNOWN_RUN;
5. `synthetic-unknown` known task -> UNKNOWN / TASK_RESULT_UNAVAILABLE;
6. host-owned stdio process lifecycle with no manually maintained daemon.

Pass 186 remains inherited controlling. This entire integration branch remains NONCLAIM.

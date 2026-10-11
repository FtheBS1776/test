# Same-context source review

Reviewer scope: fresh static review of the new consumer boundary and its focused tests after implementation. Same controller/model/context lineage; this is not strict-blind, independent-root or external assurance.

Reviewed `plugin_consumer/consumer.py` against `CONTRACT.md`, the accepted adapter pin, the L7/L2 correspondence and the current MCP/plugin facts recorded in `EXTERNAL_SPEC.md`.

Findings:

- The implementation loads only the exact accepted adapter SHA-256 `9627bc0967e4b6115f405671be8a2c60498101e276d96062d55572537f2769d2`.
- Tool exposure remains exactly `get_run_status` and `get_task_result`; accepted descriptions/input schemas are preserved. Added annotations match the actual read-only, bounded, non-open-world behavior.
- Structured consumer arguments are strict-JSON snapshotted and bounded before one adapter call. No caller/MCP identifier is treated as Genie authority. The generated correlation token is checked only for synchronous reply integrity.
- Adapter semantic dictionaries are preserved in structured and text output. `PASS`, `CONFIRMED`, `UNKNOWN`, `MISMATCH` and `REJECT` are not promoted/demoted through MCP `isError`.
- Wrapper-integrity failures are generic and sanitized; no exception detail is leaked and no retry occurs.
- No write/control/event/driver operation is exposed.
- No server/transport/authentication/SDK/provider/backend/concurrency/autonomy claim is introduced.

Adversarial checks cover malformed JSON trees, size bounds, unsupported tool names, correlation mismatch, malformed/non-dictionary adapter output, adapter exception, metadata detachment and source-pin failure.

One earlier test-harness defect was corrected: the source-pin test initially remained under the fake-loader patch and therefore failed to exercise the real source loader. That was a test defect only; no source repair followed.

Disposition: **NO CONCRETE DEFECT FOUND within the bounded consumer contract.** Remaining server/transport/authentication/install/concurrency/autonomy claims stay OPEN/HOLD as separately stated.

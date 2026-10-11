# Separate static review — same controller lineage, not independent-root

Scope: exact `shared_interfaces/mcp_consumer.py` after the first-pass repair. This review did not edit source and does not claim blind or independent evidence.

Reviewed invariants: exact pin to the accepted function adapter; no direct core/store/provider path; exact two-name tool set; exact description/schema projection; explicit read-only MCP annotations; no caller-selected path/verifier; correlation used only for the immediate synchronous adapter reply; strict output dictionary decoding; no retries; result-text notice retention; no transport/server/backend/model/authentication behavior.

First-pass defect preserved in the record: deterministic invalid caller JSON values were initially collapsed into `UNKNOWN`. That was semantically wrong because invalid input is known. Root separated input serialization from adapter-outcome handling so non-JSON inputs now return `REJECT/INVALID_ARGUMENTS`; malformed or uncorrelated adapter outcomes remain `UNKNOWN/MCP_CONSUMER_OUTCOME_UNKNOWN`.

Post-repair disposition: ACCEPT for the bounded local projection. No additional concrete blocking source defect found. Remaining MCP connectivity, authentication, remote isolation, public plugin review and prompt-injection resilience are outside this source and remain unestablished.

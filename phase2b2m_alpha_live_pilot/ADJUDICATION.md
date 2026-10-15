# Adjudication

Decision: **PHASE 2B2 ALPHA LIVE PILOT UNKNOWN - NONCLAIM**.

Exactly one authenticated alpha `exec` model turn entered. Windows Job
assignment was verified before the semantic request was written to stdin. The
logical operation is durably terminal `UNKNOWN`, with `preserve=true`,
`allow_new_invocation=false`, and retry count zero.

The child wrote the exact requested schema object to its independent last-message
file, but the JSON event stream contained a shape outside the conservative
allowlist. Because the bounded launcher did not retain the raw JSONL on this
failure path, the discrepancy cannot be resolved authoritatively. The worker
result was therefore not submitted, reviewed, delivered, or accepted.

The Job recorded two total members and zero active members after one termination
attempt. The failure path retained the member count but not both image identities,
so it does not satisfy an exact live member-image claim. A fresh destination
readback reports `UNKNOWN / TASK_RESULT_UNAVAILABLE`. No alpha process remains.

There is no retry, replacement, refund, reset, alternate launcher, Phase 2C
progression, broader mutation, main merge, promotion/freeze, spending, production
claim, or EXP010 activity.


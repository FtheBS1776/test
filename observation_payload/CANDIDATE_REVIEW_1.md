# Exact observation formatter candidate review — NONCLAIM

Disposition: NO_DEFECT_FOUND in static scope against the fixed contract. This is not proof of defect absence or an accepted journal observation; root decides and executes the frozen checks.

## Subject and method

Independently computed `observation_payload/output/observe_payload_1.py` SHA256 `92d1de6d5cda36689aa1506b03dffe8549f905e0f16e0d99fc5c89a990c578cb` and size6940 bytes. Both match the nominated subject and STATUS_1.json. Its task ID `genie-observe-payload-20261009`, input SHA256 `c4f57482e6f2d65fa1a90ec3dcd644df807d9e78dc04113a6f510444e574e555` and attempt1 agree with PLAN.json. This checks consistency, not issuer authentication.

Read CONTRACT.md, CORRESPONDENCE.md and PRIMARY_RESEARCH.md, plus existing bridge identifier/canonical helpers, runner token/callback fields and journal observe validation for interface correspondence. No candidate execution, import, compilation or tests; no acceptance suite/results read; no source changes.

## Adversarial source analysis

Dispatch, request and token require exact dicts, exact field sets and exact string keys. Action/outcome require exact strings. Attempts require exact int1..4 on both sides before equality, preventing bool/float equality from passing the projection check. Task/input/attempt are checked against the supplied token; run/task/goal/feedback/accepted agent conform to the fixed stripped nonempty string limit. Digests are exactly lowercase64 hexadecimal characters. The helper copies slot/call IDs without regenerating them and does not inspect current ledgers.

Evidence must be an exact nonempty dict. Recursive inspection permits only the fixed strict-JSON types, checks exact string keys and strict UTF8 strings, rejects nonfinite floats and detects active-ancestor cycles. Repeated noncyclic container aliases are allowed and become detached through the JSON roundtrip. Canonical UTF8 byte sizing uses the required sorted compact non-ASCII serialization with allow_nan=False, matching existing journal conventions for valid strict JSON. String evidence, tuples, nonstring keys, subclasses, lone surrogates and excessive nesting/serialization failures do not yield a payload. ValueError, TypeError, RecursionError and OverflowError are normalized to ValueError. Input token/evidence mutation after a successful return cannot mutate the returned containers.

UNKNOWN requires null agent and stays UNKNOWN; accepted outcome requires a valid agent. The resulting exact keys supplied/outcome/agent/evidence match runner observe-envelope usage. No status, permission or proof field is introduced. A syntactically correct historical dispatch can render even when stale or forged; this is explicitly permitted formatting, and actual runner/current-record validation remains required. Rendering must not be counted as worker execution, authenticated evidence, callback acceptance or relaunch permission.

CLI argument actions reject repeated flags; abbreviations, unsupported arguments, missing required flags and invalid outcomes fail through the custom parser. Files use bounded binary reads of65537 bytes with regular-file fstat before reading, strict UTF8 decoding, duplicate-key rejection at every JSON object and rejection of nonstandard constants. Post-decode tree inspection also rejects overflow-to-infinity numeric forms and escaped lone surrogates. Unix O_NONBLOCK avoids the ordinary FIFO-writer wait before nonregular rejection; there is no general IO deadline, host-path confinement or cross-platform assurance claim.

Success serializes before stdout writing and emits only the canonical envelope/newline. Expected argument/file/decode/shape failures occur before that write and emit the fixed REJECT/scope object on stderr, without raw evidence or error detail on stdout. Output-channel failures such as a broken stdout pipe are distinct from the contract's input-failure guarantee; no atomic stdout publication is claimed. The helper contains no file writes, ledger access, model calls, imports of dynamic engine dependencies, network, subprocesses or installations.

## Proportional root follow-ups

Confirm the frozen cases cover exact/bool/float attempts, crossed request-token identity, extras and wrong wrappers, string evidence, nested duplicate keys, 1e999/nonfinite values, cycles/subclasses/tuples, key/value surrogates, deep recursion, exact canonical UTF8 boundary/one-byte-over, and mutation of input containers after return. Check file-size boundary, nonregular/FIFO behavior on the actual Unix host, repeated CLI flags and byte-exact stdout/stderr/exit behavior on malformed inputs. A useful interface check renders UNKNOWN and an accepted envelope against a saved valid dispatch, then lets the unchanged callback decide separately; do not reinterpret formatter success as callback acceptance or grant new invocation from UNKNOWN.

Same configured model/host/ancestry as other roles, not independent evidence or strict-blind review. Findings apply only to the exact hashed candidate. Root tests/adjudication and exact accepted-code destination readback remain separate. Existing scoped HOLDs remain; no promotion, freeze, spending, deployment, provider/framework installation, EXP010 or old experiment was performed.

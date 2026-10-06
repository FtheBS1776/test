# Continuing-controller preexecution cross-check

No fresh blind review or authority transition is claimed. Prior correspondence, initial critique and primary-source research are recorded in PREEXEC.md.

Local attempt01 completed once. The reviewed offline verifier independently requires exact loopback commands, full transaction comparisons/input, atomic head/receipt key metadata, cluster/member identity, isolation before quorum commit, actual G0 after majority G1 normal reads, normal read deadline failure, HOLD without diagnostic authority, convergence with unchanged membership, no second write on retry, three original process exits and no remaining relay workers/connections.

Four semantic alterations, each with recalculated manifests, were rejected: diagnostic authorized, successor labeled stale, read reordered before commit, and changed cluster identity. Verifier development corrected backend list shape, cleanup field name and proto3 omitted false serialization; no database test was rerun for these corrections.

GitHub path: authorized public FtheBS1776/test, fresh exact-branch push, pinned checkout/upload actions, contents:read, no secrets/cache/billing change, standard ubuntu-24.04, five-minute job bound, one-day artifact retention, upload always including failures. Existing files/main are untouched. Controller checks exact commit diff before branch creation; no existing R2/beacon workflow file is modified. Bootstrap peer sender headers are routing observations only. Source/runtime/manifest/run/attempt binding is integrity and provenance evidence, not external trust attestation.

Wrapper stage bounds: runtime preparation65s, driver120s, verifier15s; owned process-group timeout cleanup inherited unchanged from validated delayed-completion wrapper. Any failure remains evidence rather than being silently repaired/rerun. Remote returned files are data; adjudicate with local reviewed code only.

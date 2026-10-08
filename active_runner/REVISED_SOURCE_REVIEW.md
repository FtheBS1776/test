# Revised runner source review

Exact inspected runner SHA-256: `d5450a38cf5aa4e9f6356b213fb15ddee2b751ba5101e6e17991ee6922363cd3`. The original REVIEW_PLAN.md remains unchanged. This is same-model/shared-ancestry source inspection, not independent evidence. No runner or candidate tests were executed.

Compared with subject `5847cadddd38e265418fea6ec742e7743f41f6f6873eb8eac66526c38edc6cf8`, token validation now distinguishes missing reservation from missing journal call and emits RECONCILE_SETUP. These states preserve the request/reservation, explicitly forbid new invocation and expose run state/stop reason. This addresses F1's undifferentiated diagnostic; it intentionally does not automatically fill uncertain setup gaps. Continued progress still requires controller reconciliation of actual host evidence.

A reservation STOP is now returned directly, including the budget reason, before journal begin. Subsequent steps with a missing reservation include stopped run state/reason in reconciliation output. This fixes F2's initial misleading host-call response; consumers should continue distinguishing persisted stop from incomplete setup.

WAITING_WORKER now promotes HOST_RECORD_INCONSISTENT to outer UNKNOWN/preserve rather than emitting an ordinary worker reconciliation action. Submit/review and delivery still require accepted host observations. This addresses F4 at the wrapper boundary without claiming host evidence is authenticated.

Stopped unprovisioned tasks now return RECONCILE_SETUP before creating their directories/stores. Stopped ACCEPTED tasks remain readback-only: they do not call delivery. Callbacks remain gated to current attempts and ACTIVE/HOLD queue entries. F3's exact historical callback rejection after completion or attempt advancement is therefore still the implementation behavior; the controller reports that this terminal policy is separately documented. I have not inspected that separate documentation and do not assert duplicate replay succeeds.

Residual operational limits: serial-host scope is required; context checks and dispatch span separate database transactions, so there is no concurrent stop/dispatch linearization guarantee. The error handler calls context twice, so concurrent queue loss can turn a structured UNKNOWN into a CLI rejection. This is not an identified unauthorized launch in the stated serial model. Full source dependencies use trusted owned-source checks rather than hostile-source isolation.

Useful root checks remain: request/reservation/journal interruption boundaries; budget-denied repair; stopped ACCEPTED with absent versus already committed sink; corrupt observation hash; exact terminal callback rejection; and full useful task acceptance with separate content review. These are recommendations, not results. No old fixture rerun, production acceptance or promotion follows.

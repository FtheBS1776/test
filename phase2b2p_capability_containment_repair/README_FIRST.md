# Phase 2B2P: capability-containment repair preflight

This directory records one fresh **no-model** repair preflight after the alpha
recovery operation ended terminal `UNKNOWN`.

The repair closes the observed Windows timing defect by opening and retaining a
handle for every Job member and hashing its executable while the member is
still active.  The one permitted fixture run verified assignment before gate
release, captured all three observed members, performed one bounded Job
termination, and verified zero active members afterward.

It also defines the fail-closed capability snapshot that a future exact,
hash-bound Codex build must emit before any semantic request is released.  No
Codex process or model turn was launched here.  The live Phase 2B2 pilot remains
blocked until that Codex-side patch is built and independently preflighted.

This is NONCLAIM evidence.  Do not interpret it as a live-worker success,
independent proof, production readiness, or authorization for Phase 2C.

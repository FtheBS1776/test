# Roadmap addendum — Phase 2B1 event transport

Phase 2B1 validates the smallest event-application transport boundary: one separate controller-only local stdio MCP tool over the existing bound callback facade. Exit criteria are exact discovery/schema/annotations, exact source and dependency pins, strict bad-input rejection, one delegation, operation/review-decision correspondence, UNKNOWN preservation with no retry, all three callbacks exercised only on disposable no-model fixtures, and preservation of Phase 2A/read-only/historical state.

**Mandatory stop:** do not launch a worker or reviewer model, register the event server globally, enable it in worker/reviewer contexts, apply a callback to a persistent run, expose `session_driver`, or add automatic progression on this checkpoint. A live Phase 2B2 isolation pilot needs a new correspondence audit and explicit choice of model/usage policy. Parent-side code must retain Genie tokens and paths; a child receives only sanitized task/candidate data and no Genie MCP tools. Same-model review remains common-cause, not independent evidence.

Phase 2C remains the later finite autonomous-driver frontier. No main merge, paid API, public endpoint, promotion/freeze, or EXP010 activity follows from this checkpoint.

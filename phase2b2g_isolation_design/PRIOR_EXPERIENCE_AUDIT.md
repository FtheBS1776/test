# Standing L7/L2/Genie/EXP010 correspondence audit

This audit was re-applied before the offline design.  It transfers constraints,
not authority or proof.

## L7

Exact executable, version, hash, flag behavior, configuration boundary, and
logical-operation identity are bindings only.  They cannot authorize a launch
or establish that isolation worked.  An upgrade is a new executable identity
and must be rebound before any process entry.

## L2

Authentication availability, configuration isolation, process containment,
protocol initialization, effective inventory observation, semantic worker
execution, review, and destination acceptance remain separate stages.  The
design does not collapse a documented flag into observed isolation.

## Genie

Every historical post-entry `UNKNOWN` remains terminal with preservation and
no new invocation.  A newly authorized upgrade/rebind is not a retry and may
not reuse an old operation identity.  Any future process entry restores the
strict `UNKNOWN`, no-retry/refund/reset/replacement/alternate-launcher rule.

## EXP010

Only evidence-discipline lessons transfer: bind identities, retain chronology,
distinguish observation from inference, and state failures explicitly.  No
EXP010 execution, authority, promotion, or semantics are used.

## Disposition

- Pure design logic, synthetic fixtures, and static no-launch checks: **ADAPT**.
- Accepted Phase 2A/2B1/2B2A/2B2B artifacts and terminal evidence: **PRESERVE**.
- Upgrade/rebind, auth changes, credential copying, Codex process entry, model
  turn, reviewer progression, and Phase 2C: **DEFER PENDING SEPARATE AUTHORITY**.
- Credential duplication, inference-only inventory acceptance, historical
  operation reuse, and retry after `UNKNOWN`: **REJECT**.

Same-host and same-provider evidence remains common-cause and non-independent.

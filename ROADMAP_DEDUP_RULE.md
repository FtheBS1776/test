# Standing Genie roadmap correspondence and deduplication rule — 2026-10-17

Status: **NONCLAIM governance rule**, additive to the existing PRIOR-EXPERIENCE UTILITY/CORRESPONDENCE rule and `shared_interfaces/EXTERNAL_INTEGRATION_POLICY.md`. Applies to future Genie, Brains, Reasoning Engine, plugin, standalone, research, cost, verification and autonomy planning. This rule does not itself authorize execution, spending, new authority, deployment, main merge, promotion, freeze, or EXP010 activity.

## One master roadmap; subordinate tracks are not competing roadmaps

Maintain one conceptually controlling Genie master roadmap. Integration phases, research programs, security hardening, standalone interfaces and experimental work are *subtracks* or evidence milestones, not measures of completion of Genie as a whole. Never name a new broad phase as if it replaces or duplicates a master-roadmap capability. Where published roadmap documents lag newer proven work, report the provenance and discrepancy without silently rewriting historical claims.

## Mandatory proposal-to-roadmap correspondence gate

Before proposing, adding, authorizing, or implementing any material new roadmap milestone, subsystem, capability, mechanism, or phase:

1. Inspect the latest accessible controlling roadmap and relevant amendments, the actual implementation and tests, current frontier/handoffs, and applicable L7/L2/Genie/EXP010 prior correspondence. Prefer exact evidence and revision identities over prior assistant summaries.
2. Compare the **semantic capability and authority boundary**, not just feature names. Inventory existing owner/components, interfaces, tests, HOLDs, dependencies, cost exposure, and user-maintenance burden. Do not infer an absent feature from an incomplete inventory.
3. Assign each proposed item one evidenced disposition:
   - **ALREADY_IMPLEMENTED** — cite its actual verified scope; do not rebuild it.
   - **ALREADY_PLANNED** — link the existing master milestone; do not duplicate it.
   - **PARTIAL_GAP** — specify the missing tested/untested contract and extend the existing owner.
   - **GENUINELY_NEW** — demonstrate a distinct user-valued outcome or authority boundary that cannot reasonably fit an existing milestone.
   - **REDUNDANT_OR_CONFLICTING** — reject or consolidate; preserve stronger prior constraints.
   - **DEFER_OR_UNKNOWN** — insufficient correspondence evidence or prerequisite; no speculative new phase.
4. Record a compact correspondence table: proposal, existing owner/reference, verified-versus-designed state, remaining gap, disposition, effect on cost/maintenance/authority. Explicitly list unresolved coverage and scoped HOLDs.
5. **Default to REUSE/ADAPT/EXTEND.** A separate new phase is exceptional and must state why consolidation cannot work, the measurable exit criterion, dependency and operating cost, authority implications, integration path, and regression/attack checks. Never build parallel authority, recovery, verification, orchestration, cost, memory/state, or policy systems merely for phase symmetry.
6. Cross-check proposed priorities against the complete Genie vision, including one-model usefulness, multiple optional agents/models, reasoning and adjudication, low-cost operation, hard budget gates, geometric reasoning, replaceable integrations, standalone operation, and reduced manual `⏩` prompts. Do not let the most recently tested integration displace higher-value master-roadmap work without an explicit priority decision.
7. Distinguish **designed**, **implemented**, **internally tested**, **live integrated**, **bounded NONCLAIM pilot**, **production-authorized**, and **unresolved HOLD**. Never promote evidence from one category into another through wording or renaming.

## Successor and authorization discipline

Every material successor handoff or roadmap amendment should link this rule, identify the latest verified frontier and master-roadmap correspondence, and state what was **reused**, **extended**, **rejected as overlap**, **genuinely added**, or **left UNKNOWN**. Reassess only when material facts change; do not generate another architecture/research/testing cycle solely to rename an already-covered feature.

Existing Pass186 inheritance, scoped HOLDs, exact-identity/currentness/UNKNOWN/no-retry constraints, no unauthorized spending or new model dispatch, and main/production/EXP010 authority boundaries remain unchanged. This document adds a planning gate, not execution authority.

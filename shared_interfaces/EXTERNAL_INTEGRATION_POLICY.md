# Genie external integration and compatibility policy — 2026-10-11

Status: roadmap governance amendment. This document does not promote, freeze, merge, deploy, spend money, or authorize EXP010 execution.

## Purpose

Genie remains a standalone, model/framework-agnostic governance core. External systems may supply transport, agents, tools, execution, policy assistance, provenance formats, observation, identity, or other replaceable capabilities, but they do not become Genie's source of authority merely by being integrated.

Reference architectures are studied before they are installed. The default outcome is to reuse an invariant or protocol idea without adding a runtime dependency.

## Hard constraints

### 1. No added recurring cost by default

- Prefer free, open-source, local, already-included, or user-owned capabilities.
- A new integration must not require a paid API, subscription, hosted service, metered infrastructure, or additional paid model merely to preserve existing Genie behavior.
- If a paid option would materially reduce total cost or uniquely enable a required capability, it remains DEFERRED until the user explicitly authorizes that spending.
- Cost claims require measurement; do not claim savings from architecture alone.

### 2. No routine user-maintained synchronization

- Genie owns adapter compatibility, configuration validation, state translation, migrations, and capability checks wherever technically practical.
- Do not require the user to periodically copy state, synchronize policies, update a second dashboard, reconcile versions, or manually mirror configuration across systems.
- One-time explicit setup that a platform inherently requires may be documented, but recurring maintenance burden is a design defect unless no practical automated alternative exists.
- Integration failure must preserve existing Genie state and must not force the user to repair unrelated systems manually.

### 3. External upgrades cannot silently change Genie semantics

- External protocol, SDK, framework, service, or model versions are isolated behind adapters.
- Do not accept unbounded automatic dependency upgrades across a semantic boundary.
- Pin or negotiate supported versions/capabilities where the external system permits it.
- Before adopting a newer version, run compatibility/conformance/regression checks against the existing Genie contract.
- An upstream change must not silently alter authority, UNKNOWN, provenance, receipts, currentness, coverage, execution identity, acceptance, STOP/budget, or fail-closed behavior.
- Unsupported, ambiguous, or semantically incompatible versions fail closed or remain on the last known-compatible path. They do not rewrite authoritative state.

## External-component adoption gate

Before materially adopting or upgrading an external system, record:

1. **Need** — What Genie requirement is being served?
2. **Replacement** — What custom code, operational burden, or risk does this remove?
3. **Cost** — Does it introduce recurring monetary cost? If yes, DEFER pending explicit user authorization unless separately authorized already.
4. **User burden** — Does it introduce recurring manual maintenance or synchronization? If yes, REJECT or redesign unless unavoidable and explicitly accepted.
5. **Semantic boundary** — Which Genie meanings must remain invariant?
6. **Version strategy** — How are supported versions pinned, negotiated, detected, tested, and rolled back?
7. **Failure mode** — What happens when the external component is unavailable, malformed, newer than supported, or semantically incompatible?
8. **Authority** — What authority remains exclusively Genie's?
9. **Decision** — `REUSE`, `ADAPT`, `REJECT`, or `DEFER`.

No external component becomes required merely because it is mature, popular, or referenced in architecture research.

## Reference-architecture correspondence lane

When a frontier materially overlaps a mature external architecture, first extract applicable invariants and attack whether they transfer to Genie. Current reference set:

- MCP: tool interoperability.
- A2A: agent interoperability; implementation is later than the current MCP plugin frontier.
- Cedar / OPA: policy separation and authorization-model lessons, not automatic replacement of Genie's explicit UNKNOWN/fail-closed semantics.
- in-toto / SLSA: provenance and attestation schema lessons.
- TUF: rollback, freeze, mix-and-match, and currentness attack lessons.
- Tessera / Sigstore / transparency systems: external witnessing and append-only history lessons.
- Temporal / LangGraph / similar runtimes: durable execution and orchestration lessons, not epistemic authority.
- SPIFFE-class systems: future remote workload-identity lessons when remote/multi-process identity is actually needed.
- OpenTelemetry-class systems: non-authoritative traces, metrics, and observation only.

For each materially related design, choose `REUSE`, `ADAPT`, `REJECT`, or `DEFER` and preserve the reasoning. Studying a reference system does not authorize installing it.

## Interface boundary

Target interoperability remains layered around one Genie core:

- MCP for tools/context exposed to supported hosts.
- A2A or a bounded adapter for external agents when that frontier is reached.
- Native/local adapters for owned workers and components.

A transport or framework may propose, execute, or report. It does not gain authority to promote claims, reinterpret historical receipts, erase UNKNOWN, bypass parent/currentness checks, or change Genie budgets merely because a protocol supports those operations.

## Compatibility acceptance rule

A newer external version is acceptable only when the adapter proves that old Genie-visible semantics remain equivalent or that an explicitly reviewed Genie contract revision is required. The preferred order is:

`existing Genie contract -> candidate-version adapter -> conformance/regression/adversarial checks -> accept or reject`

Not:

`dependency auto-updates -> Genie behavior changes -> repair afterward`

If equivalence cannot be established, retain the prior supported version when safe and available, otherwise mark the integration unavailable/UNKNOWN as appropriate without corrupting authoritative state.

## Cost and maintenance objective

External integration should reduce total implementation burden, runtime cost, user intervention, or risk. If it adds cost, maintenance, and semantic coupling without removing more than it adds, it does not belong in the default Genie architecture.

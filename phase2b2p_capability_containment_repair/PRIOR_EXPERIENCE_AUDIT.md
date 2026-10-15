# L7/L2/Genie/EXP010 correspondence audit

The standing audit was completed before design and execution.

- **L7:** capture raw evidence before interpretation; bind executable, policy,
  model, sandbox, and logical-operation identity by exact values and digests.
- **L2:** keep process containment, capability attestation, event parsing,
  untrusted worker output, and destination readback as separate evidence
  layers.  No single JSON event stream is authoritative.
- **Genie:** the future child may receive only the minimal worker request.  It
  receives no Genie token, queue path, owned-root path, registry path, mutation
  tool, callback, historical run state, or authority-bearing secret.
- **EXP010:** only its evidence discipline transfers.  EXP010 was not read,
  mutated, launched, promoted, frozen, or otherwise exercised.

The two earlier live `UNKNOWN` operations remain terminal and unchanged.  This
repair preflight used only a fresh no-model fixture and created no replacement
worker result.

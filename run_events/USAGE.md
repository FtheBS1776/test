# Record one trusted-host event

A trusted active host can now use three shared components with the same configured registry: GenieStatusTools reads status/results, GenieRunController advances an existing saved run once, and GenieRunEvents records one worker observation, candidate submission or root review decision. All reuse the existing core. No provider, server or background loop is installed.

From repository root, this example lists metadata only; it opens no run stores and records no event:

```bash
python3 -B - <<'PY'
import json
from shared_interfaces.run_events import GenieRunEvents
host = GenieRunEvents({'current': {
    'queue': 'run_events/trial/queue.sqlite',
    'run_id': 'genie-host-events-run-20261010',
    'owned_root': 'run_events/trial/work',
}})
print(json.dumps(host.tools(), sort_keys=True))
PY
```

The following is illustrative MUTATING host code. token must be the exact saved dispatch token; agent/text/evidence must describe the actual returned worker; decision/reason must come from the host's separate content review. It is not executable example data and must not be replayed against the completed trial.

```python
reply = host.call('apply_run_event', {
    'run_name': 'current',
    'operation': operation,  # observe, submit or review
    'supplied': token,
    'payload': payload,
})
```

| Operation | Exact payload fields | Core response in APPLIED.result |
|---|---|---|
| observe | outcome, agent, evidence | RECORDED or DUPLICATE |
| submit | agent, text | SUBMITTED or DUPLICATE |
| review | candidate_hash, decision, reason | ACCEPT, REPAIR or DUPLICATE |

For observe, outcome is OBSERVED_ACCEPTED with actual nonempty agent, or UNKNOWN with null agent. evidence is a nonempty strict JSON object, at most16000 canonical UTF8 bytes. Observation is a trusted-host assertion, not authenticated remote model proof. For submit, text is nonblank and at most12000 UTF8 bytes. For review, candidate_hash is the exact lowercase SHA256, decision ACCEPT/REPAIR, reason a trimmed nonempty identity up to200characters. The method records caller-adjudicated review; it never chooses the decision or verifies semantic correctness automatically.

Every call supplies exactly run_name, operation, supplied and payload. supplied has exact run_id/task_id/input_sha256/attempt/slot_id/call_id fields from the saved action. No paths, new policies, budgets or replacement identities are accepted. Current records remain the unchanged runner's validation boundary. Registry is trusted local configuration, not remote user authorization. Do not expose this method through the read-only CLI or catalog.

APPLIED acknowledges an allowed callback reply only. It does not mean task completion or release content into authority. UNKNOWN after entry means preserve original records and reconcile the original worker/attempt; a record may have committed before the response was lost. No automatic retry/refund/replacementworker. REJECT before callback grants no permission. DUPLICATE describes exact existing core behavior, not a blanket safe-retry policy.

Use the existing [active-host guide](../run_control/OPERATOR_GUIDE.md) for the full action sequence. The external host dispatches/awaits workers and performs separate content review. It may continue saved authorized tasks immediately while active; these methods install no loop or after-session runtime. Respect fresh readback, HOLD/STOP/budget limits. Hosting deferred; Pass186/NONCLAIM/scopedHOLD and no promotion/freeze/spending/mainmerge/deploy/EXP010 remain.

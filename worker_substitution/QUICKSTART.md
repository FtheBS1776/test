# Active-host runner CLI quickstart — NONCLAIM

Run from the repository root with Python 3.12 and the reviewed, pinned source files intact. No installs or provider keys are needed for this local fixture. Use a new disposable directory selected by `GENIE_CLI_DEMO_ROOT`; the script creates it exclusively and fails before overwriting an existing directory. It never resets a prior queue or closed run.

The queue CLI is `python3.12 -B run_queue/run_policy.py QUEUE OPERATION`; `init` and `enqueue` take their policy/plan JSON directly on stdin. Runner syntax is `python3.12 -B active_runner/runner.py QUEUE RUN_ID OWNED_ROOT OPERATION`. Operations are `step`, `observe`, `submit`, `review`. Callback stdin contains `supplied` with the exact emitted token, plus operation fields; `token` is not the callback argument name. The token binds run, task, input hash, attempt, reservation slot and host call. Workers do not select destination paths.

On a real `INVOKE_WORKER`, the active external Work host performs the model call once, records its observed accepted agent, and submits that agent's candidate. Python emits actions; it does not call a model. A separate root/controller content review must decide ACCEPT or REPAIR for the exact candidate hash. Model-produced text is not self-authorizing, and routing checks do not prove its correctness. A REPAIR may permit another bounded attempt; it does not refund the first reservation. Unknown launches consume their reservation and require reconciliation.

**The following block is a deterministic NO MODEL CALL fixture.** The fake agent and candidate simulate host callbacks solely to exercise the CLI. It reserves one workflow slot, not one observed live model call; reservations measure neither tokens nor dollars. Fixture acceptance is an exact-byte controller check, not a model-quality evaluation. Real root-host worker substitution is separate evidence and cannot be established by running this block.

```bash
set -euo pipefail
: "${GENIE_CLI_DEMO_ROOT:?Set this to a NEW disposable directory before running}"
python3.12 -B - <<'PY'
import hashlib, json, os, pathlib, subprocess
root = pathlib.Path(os.environ['GENIE_CLI_DEMO_ROOT']).absolute()
root.mkdir()  # Exclusive; existing paths fail before queue/task writes.
owned = root / 'owned'
owned.mkdir()
queue = root / 'queue.sqlite'
run_id = 'genie-cli-fixture-no-model'
task_id = 'fixture-report'
candidate = 'Deterministic CLI fixture: NO MODEL CALL.\n'
agent = 'fixture-agent-NO-MODEL-CALL'

def cli(script, args, body=None, expected_code=0):
    result = subprocess.run(['python3.12', '-B', script, *map(str, args)],
        input=None if body is None else json.dumps(body),
        text=True, capture_output=True)
    if result.returncode != expected_code:
        raise RuntimeError((script, result.returncode, result.stdout, result.stderr))
    return json.loads(result.stdout)

def q(operation, body=None):
    return cli('run_queue/run_policy.py', [queue, operation], body)

def runner(operation, body=None, expected_code=0):
    return cli('active_runner/runner.py', [queue, run_id, owned, operation], body, expected_code)

def status():
    return cli('active_runner/run_status.py', [queue, run_id, owned])

policy = {'run_id': run_id, 'max_tasks': 1, 'max_model_calls': 1,
          'effect_scope': 'owned-local-report-inbox'}
plan = {'task_id': task_id, 'goal': 'Publish deterministic CLI fixture report',
        'input_sha256': hashlib.sha256(b'NO MODEL CALL fixture input v1').hexdigest(),
        'max_attempts': 1}
assert q('init', policy) == 'INITIALIZED'
assert q('enqueue', plan) == 'ENQUEUED'
first = runner('step')
assert first['action'] == 'INVOKE_WORKER'
token = first['token']
assert token['run_id'] == run_id and token['attempt'] == 1
waiting = runner('step')
assert waiting['action'] == 'RECONCILE_WORKER'
assert waiting['token'] == token and waiting['allow_new_invocation'] is False
assert q('status')['reserved_model_calls'] == 1  # Repeated step did not relaunch.
assert runner('observe', {'supplied': token, 'outcome': 'OBSERVED_ACCEPTED',
    'agent': agent, 'evidence': {'fixture': 'NO MODEL CALL', 'source': 'deterministic CLI demo'}}) == 'RECORDED'
assert runner('submit', {'supplied': token, 'agent': agent, 'text': candidate}) == 'SUBMITTED'
review = runner('step')
assert review['action'] == 'REVIEW_CANDIDATE'
assert review['candidate'] == candidate
assert review['candidate_sha256'] == hashlib.sha256(candidate.encode()).hexdigest()
before = status()
assert before['tasks'][0]['workflow']['state'] == 'REVIEW'
assert before['tasks'][0]['fresh_sink']['status'] == 'UNKNOWN'
# Separate controller fixture review: approve only the exact checked bytes.
assert runner('review', {'supplied': review['token'],
    'candidate_hash': review['candidate_sha256'], 'decision': 'ACCEPT',
    'reason': 'Exact deterministic fixture bytes checked; NO MODEL CALL'}) == 'ACCEPT'
completed = runner('step')  # Accepted delivery plus fresh exact sink readback.
assert completed['action'] == 'TASK_COMPLETE'
assert completed['result']['status'] == 'COMPLETE'
assert completed['result']['fresh_destination'] == 'CONFIRMED'
stopped = runner('step')
assert stopped['action'] == 'STOP' and stopped['reason'] == 'ALL_TASKS_COMPLETE'
assert runner('step')['reason'] == 'ALL_TASKS_COMPLETE'
final = status()  # Fresh subprocess; historical queue COMPLETE alone is insufficient.
assert final['status'] == 'PASS'
assert final['queue_history']['state'] == 'STOPPED'
assert final['queue_history']['stop_reason'] == 'ALL_TASKS_COMPLETE'
assert final['queue_history']['reserved_model_calls'] == 1
assert final['tasks'][0]['queue_entry_history'] == 'COMPLETE'
assert final['tasks'][0]['workflow']['state'] == 'DELIVERED'
assert final['tasks'][0]['fresh_sink']['status'] == 'CONFIRMED'
terminal = runner('submit', {'supplied': token, 'agent': agent, 'text': candidate}, expected_code=2)
assert terminal['action'] == 'REJECT'  # Terminal callback is not fresh permission.
print(json.dumps({'fixture': 'NO MODEL CALL', 'demo_root': str(root),
                  'reserved_slots': 1, 'fresh_sink': 'CONFIRMED',
                  'stop_reason': 'ALL_TASKS_COMPLETE'}, sort_keys=True))
PY
```

Every CLI call in the block is a fresh subprocess. Keep the resulting files for inspection; choose a different new directory for a separately authorized demo. Do not run a loop that creates successor runs to bypass budget STOP.

| Response | Operator action |
|---|---|
| INVOKE_WORKER | Active trusted Work host may dispatch this newly reserved call once. Save the exact token. |
| RECONCILE_WORKER | Inspect the existing worker/journal; no new invocation permission. Even an UNKNOWN host outcome does not authorize relaunch. |
| RECONCILE_HOST | Preserve and investigate existing reservation/call uncertainty; no new launch permission. |
| RECONCILE_SETUP | Preserve the setup gap and inspect existing state; do not recreate files, reset the budget or relaunch. |
| UNKNOWN | Preserve and investigate the reported partial/inconsistent state. Interrupted provisioning can appear here. |
| REVIEW_CANDIDATE | Inspect exact candidate bytes/hash; root reviews content separately. |
| TASK_COMPLETE | One task has exact fresh destination readback; call step to select remaining bounded work or persist STOP. |
| RECONCILE_DESTINATION | Accepted work lacks confirmation; inspect destination without assuming completion. |
| HOLD | Keep the task held; this runner has no implicit release/reset. |
| STOP | Obey its reason, including ALL_TASKS_COMPLETE or CALL_BUDGET_EXHAUSTED. No hidden retry or successor run. |
| REJECT | Callback/CLI failure; inspect binding or workflow state. Stale/terminal callbacks are rejected conservatively. |

Read-only diagnostics use `python3.12 -B active_runner/run_status.py QUEUE RUN_ID OWNED_ROOT`. Top-level PASS means the diagnostic completed; inspect each task's `fresh_sink`. Queue completion is historical. Missing or partial per-task stores yield UNKNOWN in that task's report; changed sink content can be MISMATCH. A missing or unreadable queue, invalid run context or missing owned root may instead produce top-level REJECT with a nonzero exit. Separate read transactions are not an atomic cross-store snapshot.

For an actual host ending or authority/dependency boundary, the queue `stop` operation takes stdin `{"reason":"HOST_ENDED"}`, `{"reason":"AUTHORITY_BOUNDARY"}` or `{"reason":"DEPENDENCY_BOUNDARY"}`. Stopped accepted work is readback-only; stopping before delivery does not authorize a new sink write. This is a serial trusted local-host prototype, not background execution, authenticated remote evidence, hostile-worker isolation or rollback resistance. Same-model reviewers share ancestry. Existing scoped HOLDs and authority boundaries remain; no promotion, freeze, deployment or EXP010 execution is implied.

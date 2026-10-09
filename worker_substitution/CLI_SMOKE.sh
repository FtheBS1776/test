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

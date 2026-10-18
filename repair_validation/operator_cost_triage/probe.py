"""Fresh disposable no-model correspondence probe; no subject mains/hooks run."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

REPO = Path('/workspace/scratch/27265db857a2/r03_isolated')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
spec = importlib.util.spec_from_file_location('cost_triage_runner', REPO / 'active_runner/runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
from shared_interfaces.session_driver import drive_run

def fresh(name):
    root = HERE / name
    root.mkdir()
    owned = root / 'owned'
    owned.mkdir()
    queue = root / 'queue.sqlite'
    run = 'triage-' + name
    r.q.initialize(queue, {'run_id': run, 'max_tasks': 1, 'max_model_calls': 1,
                           'effect_scope': 'owned-local-report-inbox'})
    r.q.enqueue(queue, {'task_id': 'task', 'goal': 'NO MODEL CALL correspondence probe',
                        'input_sha256': hashlib.sha256(b'no model input').hexdigest(),
                        'max_attempts': 1})
    return queue, run, owned

queue, run, owned = fresh('runner_default')
action = r.step(queue, run, owned)
status = r.q.status(queue)
assert action['action'] == 'INVOKE_WORKER'
assert status['reserved_model_calls'] == 1
assert status['cost_admission']['reserved_micro_usd'] == 0
assert status['cost_admission']['policy']['quotes'] == {}
assert status['cost_admission']['policy']['mode'] == 'DISABLE_ALL'
with r.b.transaction(queue, False) as db:
    assert db.execute('SELECT count(*) FROM cost_actions').fetchone()[0] == 0
admission = r.q.admit_action(queue, action['token'], 'author', 'worker', 0, 'asserted-free')
assert admission['action'] == 'HOLD'
assert admission['reason'] == 'COST_QUOTE_NOT_APPROVED'
print(json.dumps({'case': 'low_level_action_is_not_monetary_permission',
                  'action': action, 'status': status, 'attempted_admission': admission}, sort_keys=True))

queue, run, owned = fresh('driver_default')
calls = []
def forbidden_hook(action):
    calls.append(action)
    raise AssertionError('No hook should be entered')
result = drive_run({'work': {'queue': str(queue), 'run_id': run, 'owned_root': str(owned)}},
                   'work', forbidden_hook, forbidden_hook)
assert calls == []
assert result['action'] == 'HOLD'
assert result['reason'] == 'COST_BOUND_UNKNOWN_OR_INVALID'
print(json.dumps({'case': 'supported_driver_denies_default', 'result': result,
                  'actual_model_calls': 0, 'hook_entries': len(calls)}, sort_keys=True))

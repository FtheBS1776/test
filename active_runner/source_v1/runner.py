"""Serial active-Work-host composition; emits actions, never calls a model."""
import argparse, hashlib, json, sqlite3, sys
from pathlib import Path
source = Path(__file__).resolve().parents[1] / 'run_queue' / 'run_policy.py'
QUEUE_SHA256 = 'ac708a3b3ad4927d58ead75a89825ffcbf43fa79a34f6a606567a38d282af543'
if hashlib.sha256(source.read_bytes()).hexdigest() != QUEUE_SHA256:
    raise ValueError('QUEUE_SOURCE_BINDING')
sys.path.insert(0, str(source.parent))
import run_policy as q
j, b = q.j, q.b
TOKEN_KEYS = {'run_id', 'task_id', 'input_sha256', 'attempt', 'slot_id', 'call_id'}

def context(queue, run_id):
    if q.inspect(queue)['status'] != 'SCHEMA_PRESENT':
        raise ValueError('QUEUE_UNKNOWN_PRESERVE')
    with b.transaction(queue, False) as db:
        policy, state, reason = q.control(db)
    if policy['run_id'] != run_id:
        raise ValueError('RUN_CONTEXT_BINDING')
    return state, reason

def paths(root, run_id, task_id):
    b.ident(run_id); b.ident(task_id)
    root = Path(root)
    if not root.is_dir():
        raise ValueError('OWNED_ROOT_MUST_EXIST')
    folder = root / b.digest(run_id) / b.digest(task_id)
    return folder, folder / 'task.sqlite', folder / 'inbox.sqlite'

def ready(ledger, sink, plan):
    if b.inspect(ledger).get('task_count') != 1 or not sink.is_file():
        raise ValueError('INCOMPLETE_PROVISIONING_PRESERVE')
    with b.transaction(ledger, False) as db:
        task, saved, _, _ = b.read(db)
        if task != plan['task_id'] or saved != b.canon(plan):
            raise ValueError('LEDGER_PLAN_BINDING')
        schemas = {'host_calls': ['attempt', 'call_id', 'request'],
                   'host_observations': ['call_id', 'event_hash', 'body']}
        if any([r[1] for r in db.execute('PRAGMA table_info(' + name + ')')] != cols
               for name, cols in schemas.items()):
            raise ValueError('INCOMPLETE_HOST_SCHEMA_PRESERVE')
    with b.transaction(sink, False) as db:
        schemas = {'reports': ['effect_id', 'target', 'body', 'payload_sha256'],
                   'applications': ['effect_id', 'applied_body']}
        if any([r[1] for r in db.execute('PRAGMA table_info(' + name + ')')] != cols
               for name, cols in schemas.items()):
            raise ValueError('INCOMPLETE_SINK_SCHEMA_PRESERVE')

def token(queue, run_id, ledger):
    context(queue, run_id)
    with b.transaction(ledger, False) as db:
        task, plan, _, n = b.read(db)
        request = db.execute('SELECT request FROM attempts WHERE n=?', (n,)).fetchone()
        call = db.execute('SELECT call_id,request FROM host_calls WHERE attempt=?', (n,)).fetchone()
    with b.transaction(queue, False) as db:
        entry = db.execute('SELECT plan,state FROM entries WHERE task_id=?', (task,)).fetchone()
        reservation = db.execute('SELECT slot_id,request FROM reservations WHERE task_id=? AND attempt=?', (task, n)).fetchone()
    if entry is None or entry[0] != plan or entry[1] not in ('ACTIVE', 'HOLD'):
        raise ValueError('QUEUE_TASK_BINDING')
    if request is None or reservation is None or reservation[1] != request[0]:
        raise ValueError('RESERVATION_REQUEST_BINDING')
    req = json.loads(request[0])
    slot = b.digest(b.canon({'kind': 'queue-call-v1', 'request': req}))
    call_id = b.digest(b.canon({'kind': 'host-invoke-v1', 'request': req}))
    if reservation[0] != slot or call != (call_id, request[0]):
        raise ValueError('CALL_SLOT_BINDING')
    return {'run_id': run_id, 'task_id': task, 'input_sha256': json.loads(plan)['input_sha256'],
            'attempt': n, 'slot_id': slot, 'call_id': call_id}

def step(queue, run_id, root):
    context(queue, run_id)
    selected = q.next_task(queue)
    if selected['action'] == 'STOP':
        return {**selected, 'run_id': run_id, 'background_execution': False}
    plan = selected['plan']
    folder, ledger, sink = paths(root, run_id, plan['task_id'])
    try:
        if not folder.exists():
            # Never complete an interrupted provisioning sequence on replay.
            folder.parent.mkdir(exist_ok=True)
            folder.mkdir()
            b.initialize(ledger); j.provision(ledger); b.create(ledger, plan)
            b.report_sink.initialize(sink)
        ready(ledger, sink, plan)
        state, reason = context(queue, run_id)
        with b.transaction(ledger, False) as db:
            workflow = b.action_db(db)
        if workflow['state'] in ('READY', 'REPAIR_READY'):
            if state != 'RUNNING':
                return {'action': 'STOP', 'reason': reason, 'run_id': run_id, 'task_id': plan['task_id']}
            action = b.request(ledger)
            if action['action'] == 'HOLD':
                q.hold(queue, plan['task_id'], action['reason']); return action
            request = action['request']
            reservation = q.reserve(queue, request, run_id)
            if reservation['action'] != 'RESERVE_ONCE':
                return {'action': 'RECONCILE_HOST', 'reservation': reservation, 'reason': 'NO_NEW_INVOCATION_PERMISSION'}
            invocation = j.begin(ledger, request['attempt'], plan['task_id'], plan['input_sha256'])
            if invocation['action'] != 'INVOKE_ONCE':
                return {'action': 'RECONCILE_HOST', 'reason': 'EXISTING_CALL'}
            return {'action': 'INVOKE_WORKER', 'token': token(queue, run_id, ledger), 'request': request}
        if workflow['state'] == 'WAITING_WORKER':
            binding = token(queue, run_id, ledger)
            return {'action': 'RECONCILE_WORKER', 'token': binding, 'host': j.status(ledger),
                    'allow_new_invocation': False}
        if workflow['state'] == 'REVIEW':
            binding = token(queue, run_id, ledger)
            host = j.status(ledger)
            if host['host_outcome'] != 'OBSERVED_ACCEPTED':
                raise ValueError('HOST_OBSERVATION_UNKNOWN')
            with b.transaction(ledger, False) as db:
                candidate, sha = db.execute('SELECT candidate,candidate_hash FROM attempts WHERE n=?', (workflow['attempt'],)).fetchone()
            if candidate is None or b.digest(candidate) != sha:
                raise ValueError('CANDIDATE_BINDING')
            return {'action': 'REVIEW_CANDIDATE', 'token': binding, 'candidate': candidate, 'candidate_sha256': sha}
        if workflow['state'] in ('ACCEPTED', 'DELIVERED'):
            token(queue, run_id, ledger)
            if j.status(ledger)['host_outcome'] != 'OBSERVED_ACCEPTED':
                raise ValueError('HOST_OBSERVATION_UNKNOWN')
            if state == 'RUNNING' and workflow['state'] == 'ACCEPTED':
                b.deliver(ledger, sink)
            completed = q.complete(queue, ledger, sink, run_id)
            return {'action': 'TASK_COMPLETE' if completed['status'] in ('COMPLETE', 'DUPLICATE') else 'RECONCILE_DESTINATION',
                    'task_id': plan['task_id'], 'result': completed}
        q.hold(queue, plan['task_id'], 'TASK_HOLD')
        return {'action': 'HOLD', 'task_id': plan['task_id']}
    except (ValueError, sqlite3.Error, OSError, KeyError, TypeError) as error:
        # Keep ACTIVE for investigation. No refund, replacement directory or relaunch.
        return {'action': 'UNKNOWN', 'task_id': plan['task_id'], 'reason': str(error),
                'allow_new_invocation': False, 'preserve': True}

def callback(queue, run_id, root, operation, supplied, **payload):
    if type(supplied) is not dict or set(supplied) != TOKEN_KEYS or type(supplied['attempt']) is not int:
        raise ValueError('CALLBACK_TOKEN_FIELDS')
    context(queue, run_id)
    if supplied['run_id'] != run_id:
        raise ValueError('CALLBACK_RUN_BINDING')
    _, ledger, sink = paths(root, run_id, supplied['task_id'])
    with b.transaction(queue, False) as db:
        row = db.execute('SELECT plan FROM entries WHERE task_id=?', (supplied['task_id'],)).fetchone()
    if row is None:
        raise ValueError('UNAUTHORIZED_TASK')
    ready(ledger, sink, json.loads(row[0]))
    if token(queue, run_id, ledger) != supplied:
        raise ValueError('CALLBACK_TOKEN_BINDING')
    bound = {k: supplied[k] for k in ('task_id', 'input_sha256')}
    if operation == 'observe':
        if set(payload) != {'outcome', 'agent', 'evidence'}:
            raise ValueError('OBSERVATION_FIELDS')
        return j.observe(ledger, supplied['attempt'], call_id=supplied['call_id'], **bound, **payload)
    if j.status(ledger)['host_outcome'] != 'OBSERVED_ACCEPTED':
        raise ValueError('HOST_OBSERVATION_UNKNOWN')
    if operation == 'submit':
        if set(payload) != {'agent', 'text'}:
            raise ValueError('SUBMIT_FIELDS')
        return b.submit(ledger, supplied['attempt'], **bound, **payload)
    if operation == 'review':
        if set(payload) != {'candidate_hash', 'decision', 'reason'}:
            raise ValueError('REVIEW_FIELDS')
        return b.review(ledger, supplied['attempt'], **bound, **payload)
    raise ValueError('CALLBACK_OPERATION')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('queue'); ap.add_argument('run_id'); ap.add_argument('owned_root')
    ap.add_argument('operation', choices=['step', 'observe', 'submit', 'review'])
    args = ap.parse_args()
    try:
        if args.operation == 'step':
            out = step(args.queue, args.run_id, args.owned_root)
        else:
            data = json.load(sys.stdin)
            out = callback(args.queue, args.run_id, args.owned_root, args.operation, **data)
        print(b.canon(out)); return 0
    except (ValueError, sqlite3.Error, OSError, KeyError, TypeError) as error:
        print(b.canon({'action': 'REJECT', 'reason': str(error)})); return 2
if __name__ == '__main__':
    raise SystemExit(main())

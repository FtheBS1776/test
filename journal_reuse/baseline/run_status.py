"""Read-only local run diagnostics; history is separate from current readback."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import types

RUNNER_SHA256 = 'd5450a38cf5aa4e9f6356b213fb15ddee2b751ba5101e6e17991ee6922363cd3'
SCOPE = 'TRUSTED_OWNED_LOCAL_OBSERVATION'


def load_runner():
    directory = Path(__file__).resolve().parent
    if directory.name == 'model_output':
        directory = directory.parent
    source = directory / 'runner.py'
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != RUNNER_SHA256:
        raise ValueError('RUNNER_SOURCE_BINDING')
    module = types.ModuleType('_status_pinned_runner')
    module.__file__ = str(source)
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        # Only the pinned owned source is executed; no archive or task code.
        exec(compile(raw, str(source), 'exec'), module.__dict__)
    finally:
        sys.dont_write_bytecode = prior
    return module


@contextmanager
def readonly(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True,
                         isolation_level=None, timeout=5)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        yield db
    finally:
        if db.in_transaction:
            db.execute('ROLLBACK')
        db.close()


def schema(db, tables):
    for name, columns in tables.items():
        actual = [row[1] for row in db.execute('PRAGMA table_info(' + name + ')')]
        if actual != columns:
            raise ValueError('INCOMPLETE_OR_UNEXPECTED_SCHEMA')


def unknown(reason):
    return {'status': 'UNKNOWN', 'reason': reason, 'preserve': True}


def journal_readback(db, b, task, plan, state, attempt):
    # Read-only counterpart to the pinned journal's consistency checks. The
    # journal helper opens mode=rw; diagnostics instead use this existing ro txn.
    out = {'status': 'UNKNOWN', 'host_outcome': 'UNKNOWN', 'agent': None,
           'call_id': None, 'observation_count': 0, 'independent_proof': False}
    try:
        schema(db, {'host_calls': ['attempt', 'call_id', 'request'],
                    'host_observations': ['call_id', 'event_hash', 'body']})
        call = db.execute('SELECT call_id,request FROM host_calls WHERE attempt=?',
                          (attempt,)).fetchone()
        if call is None:
            out['reason'] = 'NO_RECORDED_HOST_CALL'
            return out
        saved = db.execute('SELECT request,agent FROM attempts WHERE n=?',
                           (attempt,)).fetchone()
        req = json.loads(call[1])
        expected = b.digest(b.canon({'kind': 'host-invoke-v1', 'request': req}))
        if (call[0] != expected or saved is None or saved[0] != call[1]
                or req.get('task_id') != task or type(req.get('attempt')) is not int
                or req['attempt'] != attempt or req.get('input_sha256') != plan['input_sha256']
                or req.get('goal') != plan['goal']):
            raise ValueError('CALL_RECORD')
        agents = []
        count = 0
        for event_hash, body in db.execute(
                'SELECT event_hash,body FROM host_observations WHERE call_id=? ORDER BY rowid',
                (call[0],)):
            event = json.loads(body)
            if (b.digest(body) != event_hash or event.get('task_id') != task
                    or event.get('input_sha256') != plan['input_sha256']
                    or type(event.get('attempt')) is not int or event['attempt'] != attempt
                    or event.get('call_id') != call[0]
                    or event.get('outcome') not in ('UNKNOWN', 'OBSERVED_ACCEPTED')):
                raise ValueError('EVENT_RECORD')
            if event['outcome'] == 'UNKNOWN':
                if event.get('agent') is not None:
                    raise ValueError('UNKNOWN_AGENT')
            else:
                b.ident(event.get('agent'))
                agents.append(event['agent'])
            count += 1
        agent = agents[-1] if agents else None
        if any(a != agent for a in agents) or agent != saved[1]:
            raise ValueError('AGENT_RECORD')
        out.update(status='OBSERVED', host_outcome='OBSERVED_ACCEPTED' if agents else 'UNKNOWN',
                   agent=agent, call_id=call[0], observation_count=count)
        return out
    except (ValueError, TypeError, KeyError, AttributeError, sqlite3.Error):
        out.update(reason='HOST_RECORD_UNKNOWN_OR_INCONSISTENT', preserve=True)
        return out


def task_report(runner, root, run_id, task_id, saved_plan, queue_state):
    b = runner.b
    out = {'task_id': task_id, 'queue_entry_history': queue_state,
           'workflow': unknown('TASK_STORE_NOT_OBSERVED'),
           'journal': unknown('TASK_STORE_NOT_OBSERVED'),
           'fresh_sink': unknown('NO_ACCEPTED_EFFECT_OBSERVED')}
    try:
        plan = json.loads(saved_plan)
        runner.q.valid_plan(plan)
        if plan['task_id'] != task_id:
            raise ValueError('QUEUE_PLAN_BINDING')
        _, ledger, sink = runner.paths(root, run_id, task_id)
        with readonly(ledger) as db:
            schema(db, {'task': ['id', 'plan', 'state', 'attempt'],
                        'attempts': ['n', 'request', 'agent', 'candidate', 'candidate_hash', 'review']})
            if db.execute('SELECT count(*) FROM task').fetchone()[0] != 1:
                raise ValueError('TASK_COUNT')
            task, stored, state, attempt = b.read(db)
            if task != task_id or stored != saved_plan:
                raise ValueError('TASK_PLAN_BINDING')
            if type(attempt) is not int or attempt < 0 or state not in (
                    'READY', 'WAITING_WORKER', 'REVIEW', 'REPAIR_READY', 'ACCEPTED', 'DELIVERED', 'HOLD'):
                raise ValueError('WORKFLOW_RECORD')
            out['workflow'] = {'status': 'OBSERVED', 'state': state, 'attempt': attempt}
            out['journal'] = journal_readback(db, b, task, plan, state, attempt)
            if state in ('ACCEPTED', 'DELIVERED'):
                try:
                    effect = b.effect_db(db)
                except (ValueError, TypeError, KeyError, AttributeError, sqlite3.Error):
                    out['fresh_sink'] = unknown('ACCEPTANCE_RECORD_INVALID')
                else:
                    try:
                        # Existing sink observer uses a fresh mode=ro connection.
                        result = b.report_sink.observe(sink, effect)
                        out['fresh_sink'] = {'status': result, 'scope': 'FRESH_EXACT_DESTINATION_READBACK'}
                    except (ValueError, TypeError, KeyError, AttributeError, sqlite3.Error, OSError):
                        out['fresh_sink'] = unknown('DESTINATION_UNREADABLE')
        return out
    except (ValueError, TypeError, KeyError, AttributeError, sqlite3.Error, OSError):
        out['workflow'] = unknown('TASK_STORE_MISSING_PARTIAL_OR_INCONSISTENT')
        out['journal'] = unknown('TASK_STORE_MISSING_PARTIAL_OR_INCONSISTENT')
        out['fresh_sink'] = unknown('TASK_STORE_MISSING_PARTIAL_OR_INCONSISTENT')
        return out


def report(queue, run_id, root):
    runner = load_runner()
    b = runner.b
    # Check the caller's run identity before task paths or any sink inspection.
    with readonly(queue) as db:
        schema(db, {'run': ['id', 'policy', 'state', 'stop_reason']})
        policy, run_state, stop_reason = runner.q.control(db)
        if policy['run_id'] != run_id:
            raise ValueError('RUN_CONTEXT_BINDING')
        b.ident(run_id)
        schema(db, {'entries': ['seq', 'task_id', 'plan', 'state', 'reason', 'completion'],
                    'reservations': ['task_id', 'attempt', 'slot_id', 'request']})
        entries = db.execute('SELECT task_id,plan,state FROM entries ORDER BY seq').fetchall()
        count = db.execute('SELECT count(*) FROM reservations').fetchone()[0]
        history = {'run_id': run_id, 'state': run_state, 'stop_reason': stop_reason,
                   'reserved_model_calls': count, 'max_model_calls': policy['max_model_calls'],
                   'scope': 'HISTORICAL_QUEUE_STATE_NOT_CURRENT_DESTINATION_PROOF'}
    if not Path(root).is_dir():
        raise ValueError('OWNED_ROOT_MUST_EXIST')
    tasks = [task_report(runner, root, run_id, *entry) for entry in entries]
    return {'status': 'PASS', 'queue_history': history, 'tasks': tasks,
            'evidence_scope': SCOPE, 'background_execution': False,
            'snapshot_scope': 'Separate read transactions; no cross-store atomic snapshot',
            'completion_claim': 'Inspect each fresh_sink; queue COMPLETE is historical only'}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('CLI_ARGUMENTS')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('queue'); parser.add_argument('run_id'); parser.add_argument('owned_root')
        args = parser.parse_args(argv)
        result = report(args.queue, args.run_id, args.owned_root)
    except Exception as exc:
        # Do not print exception text that might contain stored content.
        reason = 'RUN_CONTEXT_BINDING' if str(exc) == 'RUN_CONTEXT_BINDING' else type(exc).__name__
        print(json.dumps({'status': 'REJECT', 'reason': reason, 'evidence_scope': SCOPE}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())

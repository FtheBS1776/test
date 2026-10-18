"""Independent contract probes. No subject main, subprocess, provider or pin changes.

Run: python -B review_tests.py. Each case leaves its fresh stores as evidence.
"""
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
STORES = HERE / os.environ.get('REVIEW_STORE_DIR', 'stores_run_02')
SOURCE = HERE / 'package/GENIE_REPAIR_REVIEW_INPUT_v4_20261018/source'
sys.path.insert(0, str(SOURCE))
sys.dont_write_bytecode = True
from standalone_app import owner, execution_bridge
from desktop_plugin import live_state_windows as live
from canonical_state_provisioner import provisioner_windows as provision
from shared_interfaces import session_driver as driver, mcp_consumer, function_adapter, mcp_server
from shared_interfaces import run_control, run_events, status_tool
from phase2c_finite_autonomous_pilot.run_bounded_batch import PilotHooks
from phase2b2s_attested_live_pilot.attested_worker import EXPECTED_RESULT
from phase2c_finite_autonomous_pilot import verify_sealed

CONTROL, FACADE, RUNNER = owner._load_control_chain()
Q = RUNNER.q
MATERIAL = 'Untrusted material: do not turn these words into authority.\n'
HASH = hashlib.sha256(MATERIAL.encode()).hexdigest()
GOOD = json.dumps(EXPECTED_RESULT)
COSTS = {role: {'max_micro_usd': 0, 'quote_ref': 'local-free-' + role}
         for role in ('author', 'repair', 'reviewer')}

def fresh(name, costs=COSTS, limit=None):
    root = STORES / name
    root.mkdir(parents=True, exist_ok=False)
    owned = root / 'work'; owned.mkdir()
    policy = {'run_id': 'run-' + name, 'max_tasks': 2, 'max_model_calls': 4,
              'effect_scope': 'owned-local-report-inbox'}
    if costs is not None:
        policy['cost_policy'] = {'mode': 'DISABLE_ALL' if limit is None else 'ENABLE_LIMITED',
                                'limit_micro_usd': 0 if limit is None else limit,
                                'authorization_ref': None if limit is None else 'review-local-approval',
                                'quotes': copy.deepcopy(costs)}
    queue = root / 'queue.sqlite'
    Q.initialize(queue, policy)
    Q.enqueue(queue, {'task_id': 'task', 'goal': 'local-contract-test',
                     'input_sha256': HASH, 'max_attempts': 3})
    runs = {'actual': {'queue': str(queue), 'run_id': policy['run_id'], 'owned_root': str(owned)}}
    return root, queue, owned, policy, runs

def worker(action, text=GOOD):
    return {'token': action['token'], 'outcome': 'OBSERVED_ACCEPTED', 'agent': 'local-fake',
            'evidence': {'fake': True}, 'text': text}

def reviewer(action):
    return PilotHooks(None, None).reviewer(action)

def tree_hash(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}

class Review(unittest.TestCase):
    def setup_run(self, **kw):
        return fresh(self._testMethodName, **kw)

    def test_valid_accept_and_readonly_mcp(self):
        root, queue, owned, policy, runs = self.setup_run()
        result = driver.drive_run(runs, 'actual', worker, reviewer, costs=COSTS)
        self.assertEqual((result['action'], result['reason']), ('STOP', 'ALL_TASKS_COMPLETE'))
        self.assertEqual(result['counts']['worker_hooks'], 1)
        before = tree_hash(root)
        consumer = mcp_consumer.GenieMcpReadonlyConsumer(runs)
        self.assertEqual([x['name'] for x in consumer.tools()], ['get_run_status', 'get_task_result'])
        for _ in range(5):
            status = consumer.call('get_run_status', {'run_name': 'actual'})['structuredContent']
            data = consumer.call('get_task_result', {'run_name': 'actual', 'task_id': 'task'})['structuredContent']
            self.assertEqual(status['status'], 'PASS')
            self.assertEqual(data['status'], 'CONFIRMED')
            self.assertEqual(data['result_text'], GOOD)
            self.assertEqual(data['content_role'], 'UNTRUSTED_ACCEPTED_TASK_DATA')
        self.assertEqual(before, tree_hash(root))

    def test_authorized_repair_can_complete(self):
        root, queue, owned, policy, runs = self.setup_run()
        seen = []
        def w(a):
            seen.append(a['token']['attempt'])
            return worker(a, '{"wrong":true}' if len(seen) == 1 else GOOD)
        result = driver.drive_run(runs, 'actual', w, reviewer, costs=COSTS)
        self.assertEqual(result['reason'], 'ALL_TASKS_COMPLETE')
        self.assertEqual(seen, [1, 2])
        self.assertEqual(Q.status(queue)['reserved_model_calls'], 2)

    def test_unknown_worker_has_no_replay_or_refund(self):
        root, queue, owned, policy, runs = self.setup_run()
        calls = []
        def w(a):
            calls.append(a)
            return {'token': a['token'], 'outcome': 'UNKNOWN', 'agent': None,
                    'evidence': {'uncertain': True}, 'text': None}
        first = driver.drive_run(runs, 'actual', w, reviewer, costs=COSTS)
        second = driver.drive_run(runs, 'actual', w, reviewer, costs=COSTS)
        self.assertEqual(first['action'], 'UNKNOWN')
        self.assertEqual(second['action'], 'RECONCILE_WORKER')
        self.assertEqual(len(calls), 1)
        self.assertEqual(Q.status(queue)['reserved_model_calls'], 1)
        with sqlite3.connect(queue) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM cost_actions').fetchone()[0], 1)

    def test_worker_identity_mutants_do_not_accept(self):
        for key in ['run_id', 'task_id', 'input_sha256', 'attempt', 'slot_id', 'call_id']:
            root, queue, owned, policy, runs = fresh(self._testMethodName + '-' + key)
            def w(a):
                r = worker(a)
                r['token'][key] = 2 if key == 'attempt' else ('f' * 64 if key.endswith('id') or key == 'input_sha256' else 'changed')
                return r
            result = driver.drive_run(runs, 'actual', w, reviewer, costs=COSTS)
            self.assertEqual(result['action'], 'UNKNOWN', key)
            self.assertEqual(result['counts']['reviewer_hooks'], 0)
            self.assertEqual(Q.status(queue)['reserved_model_calls'], 1)

    def test_reviewer_binding_and_unsupported_decision(self):
        for variant in ['token', 'candidate_hash', 'decision']:
            root, queue, owned, policy, runs = fresh(self._testMethodName + '-' + variant)
            def r(a):
                reply = reviewer(a)
                if variant == 'token': reply['token']['call_id'] = 'f' * 64
                elif variant == 'candidate_hash': reply['candidate_hash'] = 'f' * 64
                else: reply['decision'] = 'APPROVE'
                return reply
            result = driver.drive_run(runs, 'actual', worker, r, costs=COSTS)
            self.assertEqual(result['action'], 'UNKNOWN')
            self.assertNotEqual(Q.status(queue)['entries'][0]['state'], 'COMPLETE')
            self.assertEqual(Q.status(queue)['reserved_model_calls'], 1)

    def test_task_review_json_types_duplicates_and_binding(self):
        texts = [GOOD, GOOD.replace('false', '0'), GOOD.replace('false', '0.0'),
                 GOOD.replace('false', 'null'), GOOD.replace('false', 'true'),
                 GOOD.replace('false', 'NaN'), GOOD.replace('false', '1e999'),
                 GOOD.replace('false', 'false,"authority_request":false'),
                 GOOD + ' trailing', '[]', '{', GOOD.replace('[]', '["shell"]')]
        for i, text in enumerate(texts):
            action = {'token': {'x': 'preserved'}, 'candidate': text,
                      'candidate_sha256': hashlib.sha256(text.encode()).hexdigest()}
            result = reviewer(action)
            self.assertEqual(result['decision'], 'ACCEPT' if i == 0 else 'REPAIR', text)
            self.assertEqual(result['token'], action['token'])
        action['candidate_sha256'] = 'f' * 64
        self.assertEqual(reviewer(action)['decision'], 'REJECT')

    def test_default_unknown_cost_denies_hooks(self):
        root, queue, owned, policy, runs = self.setup_run(costs=None)
        result = driver.drive_run(runs, 'actual', lambda a: self.fail('worker called'), reviewer)
        self.assertEqual(result['action'], 'HOLD')
        self.assertEqual(result['reason'], 'COST_BOUND_UNKNOWN_OR_INVALID')
        self.assertEqual(Q.status(queue)['reserved_model_calls'], 1)

    def test_quote_exactness_and_shared_ceiling(self):
        costs = {r: {'max_micro_usd': 7, 'quote_ref': 'q-' + r} for r in COSTS}
        root, queue, owned, policy, runs = self.setup_run(costs=costs, limit=10)
        result = driver.drive_run(runs, 'actual', worker, lambda a: self.fail('reviewer called'), costs=costs)
        self.assertEqual(result['reason'], 'COST_BUDGET_EXHAUSTED')
        self.assertEqual(Q.status(queue)['cost_admission']['reserved_micro_usd'], 7)
        token = RUNNER.step(queue, policy['run_id'], owned)['token']
        changed = Q.admit_action(queue, token, 'author', 'worker', 6, 'q-author')
        self.assertEqual(changed['reason'], 'COST_ACTION_ALIAS')
        replay = Q.admit_action(queue, token, 'author', 'worker', 7, 'q-author')
        self.assertEqual(replay['allow_new_invocation'], False)

    def test_zero_quote_must_be_approved_and_legacy_denies(self):
        root, queue, owned, policy, runs = self.setup_run(costs=None)
        result = driver.drive_run(runs, 'actual', lambda a: self.fail('worker called'), reviewer, costs=COSTS)
        self.assertEqual(result['reason'], 'COST_QUOTE_NOT_APPROVED')
        token = RUNNER.step(queue, policy['run_id'], owned)['token']
        with sqlite3.connect(queue) as db: db.execute('DROP TABLE cost_actions')
        result = Q.admit_action(queue, token, 'author', 'other', 0, 'local-free-author')
        self.assertEqual(result['reason'], 'COST_SCHEMA_UNAVAILABLE')

    def test_stop_blocks_after_progress_and_inflight_is_not_cancelled(self):
        root, queue, owned, policy, runs = self.setup_run()
        def notify(a): Q.stop(queue, 'HOST_ENDED')
        result = driver.drive_run(runs, 'actual', lambda a: self.fail('worker called'), reviewer,
                                  notify=notify, costs=COSTS)
        self.assertEqual(result['action'], 'STOP')
        self.assertEqual(result['reason'], 'HOST_ENDED')
        result = Q.admit_action(queue, RUNNER.token(queue, policy['run_id'], RUNNER.paths(owned, policy['run_id'], 'task')[1]),
                                'author', 'worker', 0, 'local-free-author')
        self.assertEqual(result['allow_new_invocation'], False)

    def test_mcp_strict_bound_and_reply_correlation(self):
        c = mcp_consumer.GenieMcpReadonlyConsumer({})
        for args in [{'run_name': float('nan')}, {'run_name': 'a' * 9000}, {'run_name': '\ud800'}, []]:
            self.assertEqual(c.call('get_run_status', args)['structuredContent']['status'], 'REJECT')
        self.assertEqual(c.call('advance_run', {})['structuredContent']['status'], 'REJECT')
        with patch.object(c._adapter, 'handle', return_value={'type': 'function_call_output', 'call_id': 'wrong', 'output': '{"status":"PASS"}'}):
            self.assertEqual(c.call('get_run_status', {})['structuredContent']['status'], 'UNKNOWN')
        a = function_adapter.GenieFunctionAdapter({})
        for raw in ['{"run_name":"a","run_name":"b"}', '{"run_name":NaN}', '{"run_name":1e999}', '[]']:
            result = a.handle({'type':'function_call','call_id':'local','name':'get_run_status','arguments':raw})
            self.assertEqual(json.loads(result['output'])['status'], 'REJECT')

    def test_sdk_pin_failure_is_closed(self):
        # No fake SDK is injected and version checks are not overridden.
        try: mcp_server._require_sdk()
        except ValueError as e:
            self.assertEqual(str(e), 'MCP_SDK_VERSION_BINDING')
            print('COVERAGE_INDETERMINATE: pinned MCP SDK unavailable/mismatched; native transport not exercised', flush=True)

    def test_public_codex_entries_deny_before_effects(self):
        from shared_interfaces import live_codex_worker
        from phase2b2m_alpha_live_pilot import alpha_exec_worker
        from phase2b2s_attested_live_pilot import attested_worker
        root = STORES / self._testMethodName; root.mkdir(parents=True)
        for module in [live_codex_worker, attested_worker]:
            kw = dict(token={}, ledger_path=root/'never.sqlite', codex_home=root/'none', working_directory=root/'none')
            if module is attested_worker: kw.update(artifact_directory=root/'none', evidence_directory=root/'none')
            else: kw.update(executable=root/'none', version='unknown')
            with patch('subprocess.Popen', side_effect=AssertionError('process entered')):
                result = module.run_once(**kw)
            self.assertEqual(result['reason'], 'LIVE_COST_BOUND_UNAVAILABLE')
            self.assertIs(result['process_entry'], False)
        self.assertEqual(list(root.iterdir()), [])

    def test_DEFECT_alpha_exec_bypasses_cost_gate_and_enters_ledger_and_popen(self):
        from phase2b2m_alpha_live_pilot import alpha_exec_worker as alpha
        root=STORES/self._testMethodName;root.mkdir(parents=True)
        scratch=root/'scratch';scratch.mkdir()
        evidence=root/'evidence';evidence.mkdir()
        fake_executable=root/'deterministic_fake_executable.txt'
        fake_executable.write_text('This file is only hashed, never executed.\n')
        ledger=evidence/'operation.sqlite'
        calls=[]
        class FakeWindowsJob:
            def __init__(self):calls.append('WindowsJob')
            def terminate(self, code):calls.append('terminate')
            def wait_for_active(self, n, seconds):return True
            def accounting(self):return {'active_processes':0,'total_processes':0}
            def close(self):calls.append('close')
        def no_process(*args,**kw):
            with sqlite3.connect(ledger) as db:
                rows=db.execute('SELECT state,preserve,allow_new_invocation FROM operation').fetchall()
            calls.append({'Popen_boundary':True,'pre_spawn_ledger':rows,'argv':args[0]})
            raise RuntimeError('DETERMINISTIC_FAKE_STOP_BEFORE_OS_PROCESS')
        with patch.object(alpha,'WindowsJob',FakeWindowsJob),patch.object(alpha.subprocess,'Popen',side_effect=no_process):
            result=alpha.run_once(token={'review':'local-fake'},ledger_path=ledger,executable=fake_executable,
                                  version='local-fake',codex_home=root/'no-auth',working_directory=scratch)
        self.assertEqual(calls[1]['pre_spawn_ledger'],[('CLAIMED',1,0)])
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertIs(result['evidence']['process_entry'],True)
        self.assertTrue((scratch/'output-schema.json').is_file())
        reproduction={'calls':calls,'result':result,'no_actual_process_or_provider_invoked':True}
        (root/'reproduction.json').write_text(json.dumps(reproduction,indent=2))
        print('DEFECT_REPRODUCED: unbounded alpha run_once reached real ledger claim and fake Popen boundary without cost admission',flush=True)

    def test_material_bridge_hashes_before_reservation_and_attaches_hooks(self):
        root, queue, owned, policy, runs = self.setup_run()
        with patch.object(execution_bridge.live, 'load_live_runs', return_value=runs):
            for mat in [None, {}, {'task':'wrong'}, {'task':MATERIAL, 'extra':'wrong'}]:
                with self.assertRaises(execution_bridge.BridgeError):
                    execution_bridge.drive('actual', worker, reviewer, costs=COSTS, materials=mat)
                self.assertEqual(Q.status(queue)['reserved_model_calls'], 0)
            seen=[]
            def wrap(fn):
                def hook(a):
                    self.assertEqual(a['task_materials'], {'text':MATERIAL,'input_sha256':HASH,'content_role':'UNTRUSTED_TASK_INPUT'})
                    seen.append(copy.deepcopy(a['token']))
                    a['task_materials']['text']='mutated local copy'
                    return fn(a)
                return hook
            result = execution_bridge.drive('actual',wrap(worker),wrap(reviewer),costs=COSTS,materials={'task':MATERIAL})
        self.assertEqual(result['reason'],'ALL_TASKS_COMPLETE')
        self.assertEqual(seen[0],seen[1])

    def test_source_pin_failure_blocks_bridge_owner_consumer(self):
        root=STORES/self._testMethodName;root.mkdir(parents=True)
        shared=root/'shared_interfaces';shared.mkdir()
        (shared/'session_driver.py').write_text('# deliberately wrong owned-source bytes\n')
        (shared/'run_control.py').write_text('# deliberately wrong owned-source bytes\n')
        (shared/'function_adapter.py').write_text('# deliberately wrong owned-source bytes\n')
        with patch.object(execution_bridge,'__file__',str(root/'standalone_app/execution_bridge.py')):
            with self.assertRaisesRegex(execution_bridge.BridgeError,'BRIDGE_SOURCE_BINDING'):execution_bridge._load_driver()
        with patch.object(owner,'__file__',str(root/'standalone_app/owner.py')):
            with self.assertRaisesRegex(owner.OwnerError,'OWNER_SOURCE_BINDING'):owner._load_control_chain()
        with patch.object(mcp_consumer,'__file__',str(shared/'mcp_consumer.py')):
            with self.assertRaisesRegex(ValueError,'ADAPTER_SOURCE_BINDING'):mcp_consumer._load_adapter()

    def test_bad_owner_create_spec_does_not_acquire_staging(self):
        with patch.object(owner.provision,'begin',side_effect=AssertionError('staging acquired')):
            for value in [{}, {'run_name':'x','plans':[],'policy':{}}, {'run_name':float('nan')}]:
                with self.assertRaisesRegex(owner.OwnerError,'OWNER_INPUT_INVALID'):owner.create_first_run(value)

    def test_wrong_configured_run_identity_has_no_invocation(self):
        root,queue,owned,policy,runs=self.setup_run()
        runs['actual']['run_id']='wrong-configured-run'
        result=driver.drive_run(runs,'actual',lambda a:self.fail('worker invoked'),reviewer,costs=COSTS)
        self.assertEqual(result['action'],'REJECT')
        self.assertEqual(Q.status(queue)['reserved_model_calls'],0)

    def test_stop_during_inflight_worker_prevents_reviewer_dispatch(self):
        root,queue,owned,policy,runs=self.setup_run()
        def w(a):Q.stop(queue,'HOST_ENDED');return worker(a)
        result=driver.drive_run(runs,'actual',w,lambda a:self.fail('reviewer invoked'),costs=COSTS)
        self.assertEqual(result['action'],'STOP')
        self.assertEqual(result['reason'],'HOST_ENDED')
        self.assertEqual(result['counts']['worker_hooks'],1)
        self.assertEqual(result['counts']['reviewer_hooks'],0)
        self.assertEqual(Q.status(queue)['reserved_model_calls'],1)

    def test_live_binding_strict_names_and_no_mutation(self):
        root, queue, owned, policy, runs = self.setup_run()
        (root/live.MARKER_NAME).write_text(json.dumps(live.MARKER_VALUE))
        registry={'actual':{'queue':'queue.sqlite','run_id':policy['run_id'],'owned_root':'work'}}
        reg=root/live.REGISTRY_NAME;reg.write_text(json.dumps(registry))
        before=tree_hash(root)
        self.assertEqual(live.validate_state_root(root),runs)
        self.assertEqual(before,tree_hash(root))
        for name in ['../queue.sqlite','/absolute','a/b','a\\b','CON','nul.txt','x:stream','x.','..']:
            registry['actual']['queue']=name;reg.write_text(json.dumps(registry))
            with self.assertRaises(live.LiveStateError): live.validate_state_root(root)
        reg.write_text('{"a":{},"a":{}}')
        with self.assertRaises(live.LiveStateError): live.validate_state_root(root)

    def test_publication_failed_move_is_unknown_single_use(self):
        root = STORES/self._testMethodName; root.mkdir(parents=True)
        stage=root/'stage';stage.mkdir();final=root/'final'
        session=provision.ProvisioningSession(root.parent,root,stage,final)
        fake={'actual':{'queue':str(stage/'queue.sqlite'),'run_id':'run','owned_root':str(stage/'work')}}
        with patch.object(provision,'_plain_directory',side_effect=lambda p,parent:Path(p)), patch.object(provision,'_validate',return_value=fake), patch.object(provision,'_move_publish',return_value=False):
            with self.assertRaisesRegex(provision.ProvisionError,'PUBLISH_UNKNOWN_PRESERVE'):session.publish()
            self.assertTrue((stage/live.MARKER_NAME).exists())
            with self.assertRaisesRegex(provision.ProvisionError,'PROVISION_SESSION_CLOSED'):session.publish()
        self.assertTrue(stage.exists())

    def test_publication_existing_final_is_preserved(self):
        root=STORES/self._testMethodName;root.mkdir(parents=True)
        stage=root/'stage';stage.mkdir();final=root/'final';final.mkdir()
        (final/'witness').write_text('existing state must survive')
        session=provision.ProvisioningSession(root.parent,root,stage,final)
        before=tree_hash(root)
        with patch.object(provision,'_plain_directory',side_effect=lambda p,parent:Path(p)),patch.object(provision,'_move_publish',side_effect=AssertionError('move attempted')):
            with self.assertRaisesRegex(provision.ProvisionError,'PROVISION_FINAL_EXISTS'):session.publish()
        self.assertEqual(before,tree_hash(root))

    def test_publication_success_then_failed_validation_is_committed_unverified(self):
        root = STORES/self._testMethodName; root.mkdir(parents=True)
        stage=root/'stage';stage.mkdir();final=root/'final'
        session=provision.ProvisioningSession(root.parent,root,stage,final)
        fake={'actual':{'queue':str(stage/'queue.sqlite'),'run_id':'run','owned_root':str(stage/'work')}}
        def move(a,b):a.rename(b);return True
        with patch.object(provision,'_plain_directory',side_effect=lambda p,parent:Path(p)), patch.object(provision,'_validate',return_value=fake), patch.object(provision,'_move_publish',side_effect=move), patch.object(provision.live,'validate_state_root',side_effect=ValueError('fake post-move fault')):
            with self.assertRaisesRegex(provision.ProvisionError,'PUBLISHED_UNVERIFIED_PRESERVE'):session.publish()
            with self.assertRaisesRegex(provision.ProvisionError,'PROVISION_SESSION_CLOSED'):session.publish()
        self.assertTrue(final.exists());self.assertFalse(stage.exists())

    def test_failed_sealed_inspection_preserves_input(self):
        root=STORES/self._testMethodName;root.mkdir(parents=True)
        trial=root/'trial';trial.mkdir();(trial/'TERMINAL.json').write_text('{"bad":true}')
        before=tree_hash(root)
        with self.assertRaisesRegex(RuntimeError,'TERMINAL_INVARIANT'):verify_sealed.inspect_sealed(root)
        self.assertEqual(before,tree_hash(root))

if __name__=='__main__':
    print(json.dumps({'python':sys.version,'platform':platform.platform(),'os_name':os.name,'source':str(SOURCE)},sort_keys=True),flush=True)
    unittest.main(verbosity=2)

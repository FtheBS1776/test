"""New driver boundary checks. Fake hooks only: NO MODEL CALL."""
import copy,hashlib,importlib.util,io,json,pathlib,sqlite3,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('driver_candidate',ROOT/'shared_interfaces/candidate/session_driver.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.home=pathlib.Path(self.tmp.name);self.queue=self.home/'queue.sqlite';self.work=self.home/'work';self.work.mkdir()
  self.events=m._load_events();self.control=self.events._load_control();self.facade=self.control._load_facade();self.runner=self.facade._load_core().load_runner();self.run='driver-new-test';self.reg={'a':{'queue':str(self.queue),'run_id':self.run,'owned_root':str(self.work)}}
  self.runner.q.initialize(self.queue,{'run_id':self.run,'max_tasks':2,'max_model_calls':4,'effect_scope':'owned-local-report-inbox'})
  self.runner.q.enqueue(self.queue,{'task_id':'task-1','goal':'new driver boundary data','input_sha256':'a'*64,'max_attempts':2});self.w=[];self.r=[]
 def worker(self,a):
  self.w.append(copy.deepcopy(a));return {'token':copy.deepcopy(a['token']),'outcome':'OBSERVED_ACCEPTED','agent':'fake-test-worker','evidence':{'scope':'NO_MODEL_CALL'},'text':'accepted new test data'}
 def reviewer(self,a):
  self.r.append(copy.deepcopy(a));return {'token':copy.deepcopy(a['token']),'candidate_hash':a['candidate_sha256'],'decision':'ACCEPT','reason':'EXACT_TEST_DATA'}
 def drive(self,**kw):
  with patch.object(m,'_load_events',return_value=self.events),patch.object(self.events,'_load_control',return_value=self.control),patch.object(self.control,'_load_facade',return_value=self.facade):return m.drive_run(self.reg,'a',kw.pop('worker',self.worker),kw.pop('reviewer',self.reviewer),**kw)
 def advance(self):return self.control.GenieRunController(self.reg).call('advance_run',{'run_name':'a'})
 def event(self,a,op,payload):return self.events.GenieRunEvents(self.reg).call('apply_run_event',{'run_name':'a','operation':op,'supplied':a['token'],'payload':payload})
 def seed_review(self):
  a=self.advance();r=self.worker(a);self.event(a,'observe',{k:r[k] for k in ('outcome','agent','evidence')});self.event(a,'submit',{k:r[k] for k in ('agent','text')});return a
 def observations(self):
  _,p,_=self.runner.paths(self.work,self.run,'task-1')
  with sqlite3.connect(p) as db:return db.execute('SELECT count(*) FROM host_observations').fetchone()[0]
 def unknown(self,out):
  self.assertEqual(out['action'],'UNKNOWN');self.assertTrue(out['preserve']);self.assertFalse(out['allow_new_invocation'])
 def test_two_task_automatic_sequence(self):
  self.runner.q.enqueue(self.queue,{'task_id':'task-2','goal':'second new driver task','input_sha256':'b'*64,'max_attempts':2});progress=[];out=self.drive(notify=progress.append)
  self.assertEqual((out['action'],out['reason']),('STOP','ALL_TASKS_COMPLETE'));self.assertEqual(out['counts'],{'advances':7,'worker_hooks':2,'reviewer_hooks':2});self.assertEqual([p['action']['task_id'] for p in progress if p['action']['action']=='TASK_COMPLETE'],['task-1','task-2']);status=self.facade.GenieStatusTools(self.reg).call('get_run_status',{'run_name':'a'});self.assertEqual([t['fresh_sink']['status'] for t in status['tasks']],['CONFIRMED','CONFIRMED'])
 def test_startup_waiting_no_worker(self):
  self.advance();out=self.drive();self.assertEqual(out['action'],'RECONCILE_WORKER');self.assertEqual((len(self.w),len(self.r)),(0,0))
 def test_startup_review_no_reviewer(self):
  self.seed_review();self.w=[];out=self.drive();self.assertEqual(out['action'],'RECONCILE_REVIEW');self.assertEqual((len(self.w),len(self.r)),(0,0))
 def test_worker_exception_charged_no_retry(self):
  def lost(a):self.w.append(a);raise RuntimeError('secret')
  out=self.drive(worker=lost);self.unknown(out);self.assertEqual(len(self.w),1);self.assertEqual(self.runner.q.status(self.queue)['reserved_model_calls'],1);self.assertEqual(self.observations(),0);self.assertNotIn('secret',json.dumps(out));self.assertEqual(self.drive()['action'],'RECONCILE_WORKER');self.assertEqual(len(self.w),1)
 def test_reviewer_exception_restart_reconcile(self):
  def lost(a):self.r.append(a);raise RuntimeError('secret')
  out=self.drive(reviewer=lost);self.unknown(out);self.assertEqual(out['counts']['reviewer_hooks'],1);self.assertEqual(self.drive()['action'],'RECONCILE_REVIEW');self.assertEqual(len(self.r),1)
 def test_entire_worker_reply_before_any_event(self):
  def bad(a):r=self.worker(a);r['text']='x'*12001;return r
  out=self.drive(worker=bad);self.unknown(out);self.assertEqual(self.observations(),0)
 def test_bool_token_rejected_before_any_event(self):
  def bad(a):r=self.worker(a);r['token']['attempt']=True;return r
  self.unknown(self.drive(worker=bad));self.assertEqual(self.observations(),0)
 def test_wrong_original_binding_rejected(self):
  def bad(a):r=self.worker(a);r['token']['call_id']='d'*64;return r
  self.unknown(self.drive(worker=bad));self.assertEqual(self.observations(),0)
 def test_detached_action_cannot_replace_original_token(self):
  def bad(a):a['token']['call_id']='c'*64;return self.worker(a)
  self.unknown(self.drive(worker=bad));self.assertEqual(self.observations(),0)
 def test_review_reply_bool_or_crossed_hash_no_review_effect(self):
  for mode in ('bool','hash'):
   # Each subcase gets fresh stores; no uncertain replay.
   case=Tests();case.setUp()
   try:
    def bad(a):r=case.reviewer(a);r['token']['attempt']=True if mode=='bool' else r['token']['attempt'];r['candidate_hash']='d'*64 if mode=='hash' else r['candidate_hash'];return r
    case.unknown(case.drive(reviewer=bad));_,p,_=case.runner.paths(case.work,case.run,'task-1')
    with sqlite3.connect(p) as db:case.assertIsNone(db.execute('SELECT review FROM attempts').fetchone()[0])
   finally:case.doCleanups()
 def test_unknown_observation_no_submit(self):
  def worker(a):return {'token':a['token'],'outcome':'UNKNOWN','agent':None,'evidence':{'scope':'unknown fake return'},'text':None}
  out=self.drive(worker=worker);self.unknown(out);self.assertEqual(self.observations(),1);self.assertEqual(len(self.r),0);self.assertEqual(self.drive()['action'],'RECONCILE_WORKER')
 def test_callback_commits_then_response_lost_no_retry(self):
  original=self.events.GenieRunEvents.call;calls=[]
  def lost(host,name,args):
   calls.append(args['operation']);original(host,name,args);raise RuntimeError('secret')
  with patch.object(self.events.GenieRunEvents,'call',lost):out=self.drive()
  self.unknown(out);self.assertEqual(calls,['observe']);self.assertEqual(self.observations(),1)
 def test_stopped_between_submission_and_review_no_hook(self):
  original=self.events.GenieRunEvents.call
  def stop(host,name,args):
   out=original(host,name,args)
   if args['operation']=='submit':self.runner.q.stop(self.queue,'HOST_ENDED')
   return out
  with patch.object(self.events.GenieRunEvents,'call',stop):out=self.drive()
  self.assertEqual(len(self.r),0);self.assertFalse(out.get('allow_new_invocation',False));self.assertNotEqual(out['action'],'TASK_COMPLETE')
 def test_duplicate_submit_does_not_grant_review_hook(self):
  original=self.events.GenieRunEvents.call
  def duplicate(host,name,args):
   out=original(host,name,args)
   if args['operation']=='submit':out['result']='DUPLICATE'
   return out
  with patch.object(self.events.GenieRunEvents,'call',duplicate):out=self.drive()
  self.assertEqual(out['action'],'RECONCILE_REVIEW');self.assertEqual(len(self.r),0)
 def test_unconfirmed_task_complete_terminal(self):
  with patch.object(self.control.GenieRunController,'call',return_value={'action':'TASK_COMPLETE','task_id':'task-1','result':{'fresh_destination':'UNKNOWN'}}):out=self.drive()
  self.assertNotEqual(out['action'],'STOP');self.assertEqual(out['counts']['advances'],1);self.assertEqual(len(self.w),0)
 def test_action_limit_preserves_reservation_without_reset(self):
  out=self.drive(max_actions=1);self.assertEqual((out['action'],out['reason']),('HOLD','DRIVER_ACTION_LIMIT'));self.assertEqual(out['counts'],{'advances':1,'worker_hooks':1,'reviewer_hooks':0});self.assertEqual(self.runner.q.status(self.queue)['reserved_model_calls'],1);self.assertEqual(self.drive()['action'],'RECONCILE_REVIEW')
 def test_notification_failure_after_delivery_preserves_effect(self):
  def lost(p):
   if p['action']['action']=='TASK_COMPLETE':raise RuntimeError('secret')
  out=self.drive(notify=lost);self.unknown(out);self.assertEqual(out['counts']['advances'],3);self.assertEqual(self.facade.GenieStatusTools(self.reg).call('get_task_result',{'run_name':'a','task_id':'task-1'})['status'],'CONFIRMED')
 def serve(self,raw,output=None):
  output=output or io.StringIO()
  with patch.object(m,'_load_events',return_value=self.events),patch.object(self.events,'_load_control',return_value=self.control),patch.object(self.control,'_load_facade',return_value=self.facade):out=m.serve_run(self.reg,'a',io.StringIO(raw),output)
  return out,output
 def test_stdio_strict_protocol_no_resync(self):
  for raw in ('', '{"kind":"worker_return","kind":"worker_return","reply":{}}\n','{"kind":"review_decision","reply":{}}\n','{"kind":"worker_return","reply":{"x":NaN}}\n','{"kind":"worker_return","reply":{"x":"\\ud800"}}\n','x'*160001+'\n'):
   case=Tests();case.setUp()
   try:out,output=case.serve(raw);case.unknown(out);case.assertEqual(case.observations(),0);case.assertEqual(out['counts']['worker_hooks'],1)
   finally:case.doCleanups()
 def test_stdio_output_failure_no_retry(self):
  class Fail(io.StringIO):
   def write(s,x):raise OSError('secret')
  out,_=self.serve('',Fail());self.unknown(out);self.assertEqual(self.observations(),0)
 def test_invalid_config_no_progression(self):
  for value in (True,0,129):
   out=self.drive(max_actions=value);self.assertEqual(out['action'],'REJECT')
  self.assertEqual(self.runner.q.status(self.queue)['reserved_model_calls'],0)
if __name__=='__main__':unittest.main(verbosity=2)

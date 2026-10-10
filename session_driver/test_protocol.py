"""Distinct transport/repair checks; fake hooks, NO MODEL CALL."""
import io,json,unittest
from unittest.mock import patch
from session_driver.test_driver import Tests,m
class Supplement(unittest.TestCase):
 def setUp(self):self.case=Tests();self.case.setUp();self.addCleanup(self.case.doCleanups)
 def test_binary_stdio_round_trip(self):
  c=self.case;writer=io.BytesIO()
  class Reader:
   def readline(s,n):
    a=json.loads(writer.getvalue().splitlines()[-1]);kind=a['kind'];reply=c.worker(a['action']) if kind=='worker_request' else c.reviewer(a['action']);return (json.dumps({'kind':'worker_return' if kind=='worker_request' else 'review_decision','reply':reply})+'\n').encode()
  with patch.object(m,'_load_events',return_value=c.events),patch.object(c.events,'_load_control',return_value=c.control),patch.object(c.control,'_load_facade',return_value=c.facade):out=m.serve_run(c.reg,'a',Reader(),writer)
  self.assertEqual((out['action'],out['reason']),('STOP','ALL_TASKS_COMPLETE'));lines=[json.loads(x) for x in writer.getvalue().splitlines()];self.assertEqual([x['kind'] for x in lines].count('worker_request'),1);self.assertEqual([x['kind'] for x in lines].count('review_request'),1);self.assertEqual(lines[-1],{'kind':'terminal','result':out})
 def test_request_flush_failure_suppresses_further_writes(self):
  c=self.case
  class Writer(io.StringIO):
   writes=0;flushes=0
   def write(s,raw):s.writes+=1;return super().write(raw)
   def flush(s):
    s.flushes+=1
    if s.flushes==2:raise OSError('lost flush response')
  writer=Writer();out,_=c.serve('',writer);c.unknown(out);self.assertEqual(writer.writes,2);self.assertEqual(c.observations(),0)
 def test_explicit_repair_fresh_bound_attempt_then_accept(self):
  c=self.case
  def review(a):r=c.reviewer(a);r['decision']='REPAIR' if a['token']['attempt']==1 else 'ACCEPT';return r
  out=c.drive(reviewer=review);self.assertEqual((out['action'],out['reason']),('STOP','ALL_TASKS_COMPLETE'));self.assertEqual([a['token']['attempt'] for a in c.w],[1,2]);self.assertEqual(out['counts'],{'advances':6,'worker_hooks':2,'reviewer_hooks':2});self.assertEqual(c.runner.q.status(c.queue)['reserved_model_calls'],2)
if __name__=='__main__':unittest.main(verbosity=2)

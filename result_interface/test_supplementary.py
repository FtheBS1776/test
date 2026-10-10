import json,shutil,sqlite3,sys,unittest
sys.dont_write_bytecode=True
from test_result_tool import ResultTests,ROOT
class AddedBindingChecks(ResultTests):
 def test_aligned_changed_input_request_no_payload(self):
  with sqlite3.connect(self.ledger) as d:req=json.loads(d.execute('SELECT request FROM attempts').fetchone()[0])
  req['input_sha256']='f'*64;body=self.runner.b.canon(req);slot=self.runner.b.digest(self.runner.b.canon({'kind':'queue-call-v1','request':req}))
  self.mutate(self.ledger,'UPDATE attempts SET request=?',(body,));self.mutate(self.queue,'UPDATE reservations SET request=?,slot_id=?',(body,slot));self.denied(self.call(),'UNKNOWN')
 def test_crossed_attempt_no_payload(self):
  self.mutate(self.ledger,'UPDATE task SET attempt=2');self.denied(self.call(),'UNKNOWN')
 def test_copied_other_task_sink_no_payload(self):
  other=next((ROOT/'host_continuation/trial/work').rglob('inbox.sqlite'));shutil.copyfile(other,self.sink);self.denied(self.call())
# Only reviewer-prompted new checks; do not rerun inherited test methods.
if __name__=='__main__':
 suite=unittest.TestSuite(AddedBindingChecks(name) for name in ['test_aligned_changed_input_request_no_payload','test_crossed_attempt_no_payload','test_copied_other_task_sink_no_payload'])
 result=unittest.TextTestRunner().run(suite);sys.exit(0 if result.wasSuccessful() else 1)

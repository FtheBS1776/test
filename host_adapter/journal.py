"""Host observation journal; emits actions but never invokes a model itself."""
import argparse,hashlib,json,sys
from pathlib import Path
BRIDGE_SHA256='6cbc9f8b0d6f2beb85e5e60927fbc3bf4ac21628daaf3f12c8aefd3780df4b89'
source=Path(__file__).resolve().parents[1]/'worker_bridge'/'bridge.py'
if hashlib.sha256(source.read_bytes()).hexdigest()!=BRIDGE_SHA256:raise ValueError('BRIDGE_SOURCE_BINDING')
sys.path.insert(0,str(source.parent))
import bridge as b

def provision(path):
 """Explicit extension only on an owned, empty freshly provisioned ledger."""
 with b.transaction(path) as db:
  if db.execute('SELECT count(*) FROM task').fetchone()[0]:raise ValueError('EXTEND_BEFORE_TASK')
  db.execute('CREATE TABLE host_calls(attempt INTEGER PRIMARY KEY,call_id TEXT NOT NULL UNIQUE,request TEXT NOT NULL)')
  db.execute('CREATE TABLE host_observations(call_id TEXT NOT NULL,event_hash TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(call_id,event_hash))')

def bound(db,n,task_id,input_sha256):
 b.response_binding(db,task_id,input_sha256)
 _,_,state,current=b.read(db)
 if type(n) is not int or n!=current or state!='WAITING_WORKER':raise ValueError('HOST_ATTEMPT_STATE')
 return db.execute('SELECT request,agent FROM attempts WHERE n=?',(n,)).fetchone()

def begin(path,n,task_id,input_sha256):
 with b.transaction(path) as db:
  request,agent=bound(db,n,task_id,input_sha256)
  call_id=b.digest(b.canon({'kind':'host-invoke-v1','request':json.loads(request)}))
  old=db.execute('SELECT call_id,request FROM host_calls WHERE attempt=?',(n,)).fetchone()
  if old:
   if old!=(call_id,request):raise ValueError('CALL_ALIAS')
   return {'action':'RECONCILE_HOST','call_id':call_id,'request':json.loads(request)}
  if agent is not None:raise ValueError('PREEXISTING_BINDING_NO_JOURNAL')
  db.execute('INSERT INTO host_calls VALUES(?,?,?)',(n,call_id,request))
  return {'action':'INVOKE_ONCE','call_id':call_id,'request':json.loads(request)}

def observe(path,n,task_id,input_sha256,call_id,outcome,agent,evidence):
 """Trusted controller observation, not authenticated remote invocation proof."""
 if outcome not in ('UNKNOWN','OBSERVED_ACCEPTED'):raise ValueError('HOST_OUTCOME')
 if outcome=='UNKNOWN' and agent is not None:raise ValueError('UNKNOWN_AGENT')
 if outcome=='OBSERVED_ACCEPTED':b.ident(agent)
 if type(evidence) is not dict or not evidence or len(b.canon(evidence).encode())>16000:raise ValueError('EVIDENCE_BOUND')
 b.ident(call_id)
 with b.transaction(path) as db:
  b.response_binding(db,task_id,input_sha256)
  if type(n) is not int:raise ValueError('HOST_ATTEMPT_STATE')
  attempt_row=db.execute('SELECT request,agent FROM attempts WHERE n=?',(n,)).fetchone()
  if attempt_row is None:raise ValueError('HOST_ATTEMPT_STATE')
  request,old_agent=attempt_row
  call=db.execute('SELECT call_id,request FROM host_calls WHERE attempt=?',(n,)).fetchone()
  if call!=(call_id,request):raise ValueError('HOST_CALL_BINDING')
  body=b.canon({'task_id':task_id,'input_sha256':input_sha256,'attempt':n,'call_id':call_id,'outcome':outcome,'agent':agent,'evidence':evidence,'issuer':'trusted-Work-controller'})
  event=b.digest(body)
  old=db.execute('SELECT body FROM host_observations WHERE call_id=? AND event_hash=?',(call_id,event)).fetchone()
  if old:
   if old!=(body,):raise ValueError('OBSERVATION_ALIAS')
   return 'DUPLICATE'
  bound(db,n,task_id,input_sha256)
  if old_agent is not None and (outcome!='OBSERVED_ACCEPTED' or old_agent!=agent):raise ValueError('OBSERVED_AGENT_CONFLICT')
  db.execute('INSERT INTO host_observations VALUES(?,?,?)',(call_id,event,body))
  if outcome=='OBSERVED_ACCEPTED':db.execute('UPDATE attempts SET agent=? WHERE n=?',(agent,n))
  return 'RECORDED'

def status(path):
 with b.transaction(path,False) as db:
  task,plan,state,n=b.read(db)
  call=db.execute('SELECT call_id,request FROM host_calls WHERE attempt=?',(n,)).fetchone()
  attempt=db.execute('SELECT request,agent FROM attempts WHERE n=?',(n,)).fetchone()
  out={'task_id':task,'attempt':n,'workflow_state':state,'call_id':None if call is None else call[0],'host_outcome':'UNKNOWN','agent':None,'observation_count':0,'action':'RECONCILE_HOST','independent_proof':False}
  if call is None:return out
  try:
   req=json.loads(call[1]);expected=b.digest(b.canon({'kind':'host-invoke-v1','request':req}))
   if call[0]!=expected or attempt is None or call[1]!=attempt[0] or req.get('task_id')!=task or req.get('attempt')!=n or req.get('input_sha256')!=json.loads(plan)['input_sha256']:raise ValueError('CALL_RECORD')
   rows=db.execute('SELECT event_hash,body FROM host_observations WHERE call_id=? ORDER BY rowid',(call[0],)).fetchall()
   events=[]
   for event_hash,body in rows:
    event=json.loads(body)
    if b.digest(body)!=event_hash or event.get('task_id')!=task or event.get('input_sha256')!=req['input_sha256'] or event.get('attempt')!=n or event.get('call_id')!=call[0] or event.get('outcome') not in ('UNKNOWN','OBSERVED_ACCEPTED'):raise ValueError('EVENT_RECORD')
    if event['outcome']=='UNKNOWN' and event.get('agent') is not None:raise ValueError('UNKNOWN_AGENT')
    if event['outcome']=='OBSERVED_ACCEPTED':b.ident(event.get('agent'))
    events.append(event)
   accepted=[e for e in events if e['outcome']=='OBSERVED_ACCEPTED']
   agent=accepted[-1]['agent'] if accepted else None
   if any(e['agent']!=agent for e in accepted) or agent!=attempt[1]:raise ValueError('AGENT_RECORD')
   out.update(host_outcome='OBSERVED_ACCEPTED' if accepted else 'UNKNOWN',agent=agent,observation_count=len(events),action=('RECONCILE_EXISTING_WORKER' if state=='WAITING_WORKER' else 'FOLLOW_WORKFLOW') if accepted else 'RECONCILE_HOST')
  except (ValueError,TypeError,KeyError):out.update(host_outcome='UNKNOWN',reason='HOST_RECORD_INCONSISTENT',action='PRESERVE_AND_INSPECT')
  return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('database');ap.add_argument('operation',choices=['provision','begin','observe','status']);a=ap.parse_args()
 if a.operation=='provision':provision(a.database);out='PROVISIONED'
 elif a.operation=='status':out=status(a.database)
 else:x=json.load(sys.stdin);out=begin(a.database,**x) if a.operation=='begin' else observe(a.database,**x)
 print(b.canon(out))
if __name__=='__main__':main()

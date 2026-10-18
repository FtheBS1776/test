"""Bounded trusted-host scheduling. Reservations count even when launch is UNKNOWN."""
import argparse,hashlib,json,sqlite3,sys
from pathlib import Path
source=Path(__file__).resolve().parents[1]/'host_adapter'/'journal.py'
EXPECTED_JOURNAL_SHA256='1d7825208cfac386acf0cd83b3505064de8c147ebb35fc6fe54864dd3950cc98'
if hashlib.sha256(source.read_bytes()).hexdigest()!=EXPECTED_JOURNAL_SHA256:raise ValueError('JOURNAL_SOURCE_BINDING')
sys.path.insert(0,str(source.parent))
import journal as j
b=j.b

def inspect(path):
 if not Path(path).is_file():return {'status':'UNKNOWN','reason':'MISSING_QUEUE'}
 try:
  with b.transaction(path,False) as db:
   expected={'run':['id','policy','state','stop_reason'],'entries':['seq','task_id','plan','state','reason','completion'],'reservations':['task_id','attempt','slot_id','request']}
   if any([r[1] for r in db.execute('PRAGMA table_info('+name+')')]!=cols for name,cols in expected.items()):return {'status':'UNKNOWN','reason':'INCOMPLETE_OR_UNEXPECTED_SCHEMA','action':'PRESERVE_AND_INSPECT'}
   control(db)
   return {'status':'SCHEMA_PRESENT'}
 except (sqlite3.Error,ValueError,TypeError):return {'status':'UNKNOWN','reason':'UNREADABLE_QUEUE'}

def valid_plan(p):
 if type(p) is not dict or set(p)!={'task_id','goal','input_sha256','max_attempts'}:raise ValueError('PLAN_FIELDS')
 b.ident(p['task_id']);b.ident(p['goal'])
 if type(p['max_attempts']) is not int or not 1<=p['max_attempts']<=4:raise ValueError('ATTEMPT_BOUND')
 h=p['input_sha256']
 if type(h) is not str or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('INPUT_HASH')

def valid_policy(policy):
 if type(policy) is not dict or set(policy) not in ({'run_id','max_tasks','max_model_calls','effect_scope'}, {'run_id','max_tasks','max_model_calls','effect_scope','cost_policy'}):raise ValueError('POLICY_FIELDS')
 cost_policy(policy)
 b.ident(policy['run_id'])
 if any(type(policy[k]) is not int or not 1<=policy[k]<=8 for k in ('max_tasks','max_model_calls')):raise ValueError('POLICY_BOUNDS')
 if policy['effect_scope']!='owned-local-report-inbox':raise ValueError('EFFECT_SCOPE')


def initialize(path,policy):
 valid_policy(policy)
 with Path(path).open('xb'):pass
 with b.transaction(path) as db:
  db.execute('CREATE TABLE run(id INTEGER PRIMARY KEY CHECK(id=1),policy TEXT NOT NULL,state TEXT NOT NULL,stop_reason TEXT)')
  db.execute('CREATE TABLE entries(seq INTEGER PRIMARY KEY,task_id TEXT NOT NULL UNIQUE,plan TEXT NOT NULL,state TEXT NOT NULL,reason TEXT,completion TEXT)')
  db.execute('CREATE TABLE reservations(task_id TEXT NOT NULL,attempt INTEGER NOT NULL,slot_id TEXT NOT NULL UNIQUE,request TEXT NOT NULL,PRIMARY KEY(task_id,attempt))')
  db.execute("CREATE TABLE cost_actions(action_id TEXT PRIMARY KEY,binding TEXT NOT NULL,max_micro_usd INTEGER NOT NULL CHECK(max_micro_usd>=0))")
  db.execute("INSERT INTO run VALUES(1,?,'RUNNING',NULL)",(b.canon(policy),))

def control(db):
 row=db.execute('SELECT policy,state,stop_reason FROM run WHERE id=1').fetchone()
 if row is None:raise ValueError('NO_RUN')
 return json.loads(row[0]),row[1],row[2]

def enqueue(path,plan):
 valid_plan(plan)
 with b.transaction(path) as db:
  policy,state,_=control(db);old=db.execute('SELECT plan FROM entries WHERE task_id=?',(plan['task_id'],)).fetchone()
  if old:
   if old!=(b.canon(plan),):raise ValueError('TASK_ALIAS')
   return 'DUPLICATE'
  if state!='RUNNING':raise ValueError('RUN_STOPPED')
  if db.execute('SELECT count(*) FROM entries').fetchone()[0]>=policy['max_tasks']:raise ValueError('TASK_LIMIT')
  seq=db.execute('SELECT coalesce(max(seq),0)+1 FROM entries').fetchone()[0]
  db.execute("INSERT INTO entries VALUES(?,?,?,'READY',NULL,NULL)",(seq,plan['task_id'],b.canon(plan)))
 return 'ENQUEUED'

def next_task(path):
 with b.transaction(path) as db:
  policy,state,reason=control(db)
  active=db.execute("SELECT task_id,plan FROM entries WHERE state='ACTIVE' ORDER BY seq LIMIT 1").fetchone()
  if active:return {'action':'RESUME_TASK' if state=='RUNNING' else 'RECONCILE_TASK','task_id':active[0],'plan':json.loads(active[1]),'run_state':state,'allow_new_invocation':state=='RUNNING','run_id':policy['run_id']}
  if state!='RUNNING':return {'action':'STOP','reason':reason}
  ready=db.execute("SELECT task_id,plan FROM entries WHERE state='READY' ORDER BY seq LIMIT 1").fetchone()
  if ready and db.execute('SELECT count(*) FROM reservations').fetchone()[0]<policy['max_model_calls']:
   db.execute("UPDATE entries SET state='ACTIVE' WHERE task_id=?",(ready[0],))
   return {'action':'START_TASK','task_id':ready[0],'plan':json.loads(ready[1]),'run_state':'RUNNING'}
  reason='CALL_BUDGET_EXHAUSTED' if ready else ('ONLY_HELD_TASKS' if db.execute("SELECT count(*) FROM entries WHERE state='HOLD'").fetchone()[0] else 'ALL_TASKS_COMPLETE')
  db.execute("UPDATE run SET state='STOPPED',stop_reason=? WHERE id=1",(reason,))
  return {'action':'STOP','reason':reason}

def reserve(path,request,run_id):
 if type(request) is not dict or set(request)!={'task_id','attempt','input_sha256','goal','feedback'}:raise ValueError('REQUEST_FIELDS')
 n=request['attempt']
 if type(n) is not int or n<1:raise ValueError('ATTEMPT_ID')
 with b.transaction(path) as db:
  policy,runstate,_=control(db)
  if run_id!=policy['run_id']:raise ValueError('RUN_CONTEXT_BINDING')
  row=db.execute('SELECT plan,state FROM entries WHERE task_id=?',(request['task_id'],)).fetchone()
  if row is None:raise ValueError('UNAUTHORIZED_TASK')
  plan=json.loads(row[0])
  if any(request[k]!=plan[k] for k in ('task_id','goal','input_sha256')) or n>plan['max_attempts']:raise ValueError('TASK_REQUEST_BINDING')
  if request['feedback'] is not None:b.ident(request['feedback'])
  body=b.canon(request);slot=b.digest(b.canon({'kind':'queue-call-v1','request':request}))
  old=db.execute('SELECT slot_id,request FROM reservations WHERE task_id=? AND attempt=?',(plan['task_id'],n)).fetchone()
  if old:
   if old!=(slot,body):raise ValueError('RESERVATION_ALIAS')
   return {'action':'RECONCILE_RESERVATION','slot_id':slot,'run_id':run_id,'charged':True}
  if runstate!='RUNNING' or row[1]!='ACTIVE':raise ValueError('RUN_OR_TASK_NOT_ACTIVE')
  last=db.execute('SELECT coalesce(max(attempt),0) FROM reservations WHERE task_id=?',(plan['task_id'],)).fetchone()[0]
  if n!=last+1:raise ValueError('ATTEMPT_SEQUENCE')
  if db.execute('SELECT count(*) FROM reservations').fetchone()[0]>=policy['max_model_calls']:
   db.execute("UPDATE run SET state='STOPPED',stop_reason='CALL_BUDGET_EXHAUSTED' WHERE id=1")
   return {'action':'STOP','reason':'CALL_BUDGET_EXHAUSTED'}
  db.execute('INSERT INTO reservations VALUES(?,?,?,?)',(plan['task_id'],n,slot,body))
  return {'action':'RESERVE_ONCE','slot_id':slot,'run_id':run_id,'charged':True}

def hold(path,task_id,reason):
 b.ident(reason)
 with b.transaction(path) as db:
  row=db.execute('SELECT state FROM entries WHERE task_id=?',(task_id,)).fetchone()
  if row is None or row[0] not in ('READY','ACTIVE','HOLD'):raise ValueError('HOLD_STATE')
  db.execute("UPDATE entries SET state='HOLD',reason=? WHERE task_id=?",(reason,task_id))

def complete(path,task_ledger,sink,run_id):
 # Two owned databases, no cross-store atomicity claim. Completion is a verified historical event.
 with b.transaction(task_ledger,False) as taskdb:
  task,plan,state,n=b.read(taskdb);effect=b.effect_db(taskdb);request=taskdb.execute('SELECT request FROM attempts WHERE n=?',(n,)).fetchone()[0]
  try:destination=b.report_sink.observe(sink,effect)
  except sqlite3.Error:destination='UNKNOWN'
 if destination!='CONFIRMED':return {'status':'UNKNOWN','reason':'DESTINATION_NOT_CONFIRMED'}
 evidence=b.canon({'task_id':task,'plan_sha256':b.digest(plan),'attempt':n,'effect_id':effect['effect_id'],'payload_sha256':b.digest(effect['payload']),'destination':'CONFIRMED','scope':'owned-local-readback'})
 with b.transaction(path) as db:
  policy,_,_=control(db)
  if run_id!=policy['run_id']:raise ValueError('RUN_CONTEXT_BINDING')
  evidence=b.canon({**json.loads(evidence),'run_id':run_id,'request_sha256':b.digest(request)})
  saved_request=db.execute('SELECT request FROM reservations WHERE task_id=? AND attempt=?',(task,n)).fetchone()
  if saved_request!=(request,):raise ValueError('COMPLETION_REQUEST_BINDING')
  row=db.execute('SELECT plan,state,completion FROM entries WHERE task_id=?',(task,)).fetchone()
  if row is None or row[0]!=plan:raise ValueError('COMPLETION_TASK_BINDING')
  if row[1]=='COMPLETE':
   if row[2]!=evidence:raise ValueError('COMPLETION_ALIAS')
   return {'status':'DUPLICATE','fresh_destination':'CONFIRMED'}
  if row[1] not in ('ACTIVE','HOLD'):raise ValueError('COMPLETION_STATE')
  if not db.execute('SELECT 1 FROM reservations WHERE task_id=? AND attempt=?',(task,n)).fetchone():raise ValueError('UNRESERVED_ATTEMPT')
  db.execute("UPDATE entries SET state='COMPLETE',completion=? WHERE task_id=?",(evidence,task))
 return {'status':'COMPLETE','fresh_destination':'CONFIRMED'}

def stop(path,reason):
 if reason not in ('HOST_ENDED','AUTHORITY_BOUNDARY','DEPENDENCY_BOUNDARY'):raise ValueError('STOP_REASON')
 with b.transaction(path) as db:
  _,state,old=control(db)
  if state=='STOPPED':return {'state':state,'reason':old}
  db.execute("UPDATE run SET state='STOPPED',stop_reason=? WHERE id=1",(reason,))
 return {'state':'STOPPED','reason':reason}

def status(path):
 with b.transaction(path,False) as db:
  p,state,reason=control(db)
  return {'cost_admission':cost_status(db,p),'run_id':p['run_id'],'state':state,'stop_reason':reason,'reserved_model_calls':db.execute('SELECT count(*) FROM reservations').fetchone()[0],'max_model_calls':p['max_model_calls'],'entries':[{'task_id':x[0],'state':x[1],'reason':x[2]} for x in db.execute('SELECT task_id,state,reason FROM entries ORDER BY seq')],'completion_scope':'historical readback; re-observe destination before relying on currentness','background_execution':False}

# Monetary admission extends this queue's existing transaction owner. No second
# database, refund/reset API, price service or invoice guarantee is introduced.
COST_ROLES = {"author", "reviewer", "repair", "tool", "service", "runner"}
COST_DEFAULT = {"mode": "DISABLE_ALL", "limit_micro_usd": 0, "authorization_ref": None, "quotes": {}}


def cost_policy(policy):
 value = policy.get("cost_policy", COST_DEFAULT)
 if type(value) is not dict or set(value) != set(COST_DEFAULT):raise ValueError("COST_POLICY_FIELDS")
 mode, limit, auth = value["mode"], value["limit_micro_usd"], value["authorization_ref"]
 if mode == "DISABLE_ALL":
  if type(limit) is not int or limit != 0 or auth is not None:raise ValueError("COST_POLICY_VALUES")
 elif mode == "ENABLE_LIMITED":
  if type(limit) is not int or not 0 < limit <= 10**15:raise ValueError("COST_POLICY_VALUES")
  b.ident(auth)
 elif mode == "ENABLE_ALL":
  if limit is not None:raise ValueError("COST_POLICY_VALUES")
  b.ident(auth)
 else:raise ValueError("COST_POLICY_MODE")
 quotes=value["quotes"]
 if type(quotes) is not dict or any(type(k) is not str or k not in COST_ROLES for k in quotes):raise ValueError("COST_QUOTES")
 for quote in quotes.values():
  if type(quote) is not dict or set(quote)!={"max_micro_usd","quote_ref"}:raise ValueError("COST_QUOTES")
  if type(quote["max_micro_usd"]) is not int or not 0 <= quote["max_micro_usd"] <= 10**15:raise ValueError("COST_QUOTES")
  b.ident(quote["quote_ref"])
 return dict(value)


def cost_status(db, policy):
 configured = cost_policy(policy)
 columns = [r[1] for r in db.execute("PRAGMA table_info(cost_actions)")]
 if columns != ["action_id", "binding", "max_micro_usd"]:
  return {"status":"UNAVAILABLE", "reason":"LEGACY_COST_SCHEMA", "policy":configured}
 return {"status":"PRESENT", "policy":configured,
         "reserved_micro_usd":db.execute("SELECT coalesce(sum(max_micro_usd),0) FROM cost_actions").fetchone()[0],
         "scope":"TRUSTED_HOST_UPPER_BOUNDS_NOT_PROVIDER_INVOICE"}


def admit_action(path, token, role, operation_id, max_micro_usd, quote_ref):
 """Reserve once before one hook. None/unknown cost never grants dispatch.

 Bounds and quote provenance must be supplied by the trusted host from a
 reviewed adapter contract. This function cannot authenticate a price claim.
 """
 def deny(reason):return {"action":"HOLD", "reason":reason, "allow_new_invocation":False, "preserve":True}
 if (type(max_micro_usd) is not int or not 0 <= max_micro_usd <= 10**15):return deny("COST_BOUND_UNKNOWN_OR_INVALID")
 if type(role) is not str or role not in COST_ROLES or type(quote_ref) is not str or not quote_ref.strip():return deny("COST_CONTEXT_INVALID")
 b.ident(operation_id);b.ident(quote_ref)
 keys={"run_id","task_id","input_sha256","attempt","slot_id","call_id"}
 if type(token) is not dict or set(token)!=keys or type(token['attempt']) is not int:return deny("COST_TOKEN_INVALID")
 token=json.loads(b.canon(token))
 with b.transaction(path) as db:
  policy,state,_ = control(db)
  budget = cost_status(db,policy)
  if budget['status'] != 'PRESENT':return deny("COST_SCHEMA_UNAVAILABLE")
  row=db.execute("SELECT plan,state FROM entries WHERE task_id=?",(token['task_id'],)).fetchone()
  reservation=db.execute("SELECT slot_id,request FROM reservations WHERE task_id=? AND attempt=?",(token['task_id'],token['attempt'])).fetchone()
  if row is None or reservation is None:return deny("COST_RESERVATION_BINDING")
  plan=json.loads(row[0]);request=json.loads(reservation[1])
  expected={'run_id':policy['run_id'],'task_id':plan['task_id'],'input_sha256':plan['input_sha256'],
            'attempt':request['attempt'],'slot_id':reservation[0],
            'call_id':b.digest(b.canon({'kind':'host-invoke-v1','request':request}))}
  if token != expected:return deny("COST_TOKEN_BINDING")
  action_id=b.digest(b.canon({'token':token,'role':role,'operation_id':operation_id}))
  binding=b.canon({'token':token,'role':role,'operation_id':operation_id,'max_micro_usd':max_micro_usd,'quote_ref':quote_ref})
  old=db.execute('SELECT binding FROM cost_actions WHERE action_id=?',(action_id,)).fetchone()
  if old:
   if old!=(binding,):return deny("COST_ACTION_ALIAS")
   return {"action":"RECONCILE_COST_ACTION", "reason":"COST_ACTION_ALREADY_RESERVED", "preserve":True, "allow_new_invocation":False}
  if state!='RUNNING' or row[1]!='ACTIVE':return deny("COST_RUN_NOT_ACTIVE")
  configured=budget['policy']
  if max_micro_usd and configured['mode']=='DISABLE_ALL':return deny("COST_CALLS_DISABLED")
  if configured['mode']=='ENABLE_LIMITED' and budget['reserved_micro_usd']+max_micro_usd>configured['limit_micro_usd']:return deny("COST_BUDGET_EXHAUSTED")
  if configured['quotes'].get(role)!={'max_micro_usd':max_micro_usd,'quote_ref':quote_ref}:return deny("COST_QUOTE_NOT_APPROVED")
  db.execute('INSERT INTO cost_actions VALUES(?,?,?)',(action_id,binding,max_micro_usd))
  return {"action":"ADMIT_ONCE", "action_id":action_id, "reserved_micro_usd":max_micro_usd}


def main():
 ap=argparse.ArgumentParser();ap.add_argument('database');ap.add_argument('operation',choices=['init','inspect','enqueue','next','reserve','hold','complete','stop','status']);a=ap.parse_args();x={} if a.operation in ('inspect','next','status') else json.load(sys.stdin)
 if a.operation=='init':initialize(a.database,x);out='INITIALIZED'
 elif a.operation=='inspect':out=inspect(a.database)
 elif a.operation=='enqueue':out=enqueue(a.database,x)
 elif a.operation=='next':out=next_task(a.database)
 elif a.operation=='reserve':out=reserve(a.database,**x)
 elif a.operation=='hold':hold(a.database,**x);out='HELD'
 elif a.operation=='complete':out=complete(a.database,**x)
 elif a.operation=='stop':out=stop(a.database,**x)
 else:out=status(a.database)
 print(b.canon(out))
if __name__=='__main__':main()

"""Bounded trusted-host task ledger. No model API, no authority promotion."""
import argparse, hashlib, json, sqlite3
from contextlib import contextmanager
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'reused'))
# Pin reused executable dependencies; this is an owned-source integrity check, not authenticity.
REUSED_SHA256={'report_sink.py': 'fe8f62eaeff8825319ea98fd76cd8bb92bc9099a5c4af24d33fecb8ac7eb4806', 'stateful_subject.py': '8ea005246f66fd413f00bad6cf0714e5704c23cc4255881ce659e682ce740131'}
for dependency,expected_sha in REUSED_SHA256.items():
 if hashlib.sha256((Path(__file__).resolve().parent/'reused'/dependency).read_bytes()).hexdigest()!=expected_sha:raise ValueError('REUSED_SOURCE_BINDING')
import report_sink
import stateful_subject as st

def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(x):return hashlib.sha256(x.encode()).hexdigest()
def ident(x):
 if type(x) is not str or not x or x!=x.strip() or len(x)>200:raise ValueError('IDENTITY')
 return x

def initialize(path):
 # Host-owned provisioning, not a hostile shared-directory primitive.
 p=Path(path)
 with p.open('xb'):pass
 db=sqlite3.connect(p,isolation_level=None)
 try:
  db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA synchronous=FULL')
  db.execute('BEGIN IMMEDIATE')
  db.execute('CREATE TABLE task(id TEXT PRIMARY KEY,plan TEXT NOT NULL,state TEXT NOT NULL,attempt INTEGER NOT NULL)')
  db.execute('CREATE TABLE attempts(n INTEGER PRIMARY KEY,request TEXT NOT NULL,agent TEXT,candidate TEXT,candidate_hash TEXT,review TEXT)')
  db.execute('COMMIT')
 finally:db.close()

@contextmanager
def transaction(path,write=True):
 db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=rw',uri=True,isolation_level=None,timeout=5)
 try:
  db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
  yield db
  db.execute('COMMIT')
 except BaseException:
  if db.in_transaction:db.execute('ROLLBACK')
  raise
 finally:db.close()

def inspect(path):
 if not Path(path).is_file():return {'status':'UNKNOWN','reason':'MISSING_LEDGER'}
 try:
  with transaction(path,False) as db:
   schemas={name:[row[1] for row in db.execute('PRAGMA table_info('+name+')')] for name in ('task','attempts')}
   if schemas!={'task':['id','plan','state','attempt'],'attempts':['n','request','agent','candidate','candidate_hash','review']}:return {'status':'UNKNOWN','reason':'INCOMPLETE_OR_UNEXPECTED_PROVISIONING','action':'PRESERVE_AND_INSPECT_NO_OVERWRITE'}
   return {'status':'SCHEMA_PRESENT','task_count':db.execute('SELECT count(*) FROM task').fetchone()[0]}
 except sqlite3.Error:return {'status':'UNKNOWN','reason':'UNREADABLE_LEDGER'}

def read(db):
 row=db.execute('SELECT id,plan,state,attempt FROM task').fetchone()
 if row is None:raise ValueError('NO_TASK')
 return row

def create(path,plan):
 if type(plan) is not dict or set(plan)!={'task_id','goal','input_sha256','max_attempts'}:raise ValueError('PLAN_FIELDS')
 ident(plan['task_id']);ident(plan['goal'])
 if type(plan['max_attempts']) is not int or not 1<=plan['max_attempts']<=4:raise ValueError('ATTEMPT_BOUND')
 if type(plan['input_sha256']) is not str or len(plan['input_sha256'])!=64 or any(c not in '0123456789abcdef' for c in plan['input_sha256']):raise ValueError('INPUT_HASH')
 with transaction(path) as db:
  rows=db.execute('SELECT id,plan FROM task').fetchall()
  if rows:
   if rows!=[(plan['task_id'],canon(plan))]:raise ValueError('TASK_ALIAS')
   return 'DUPLICATE'
  db.execute('INSERT INTO task VALUES(?,?,?,0)',(plan['task_id'],canon(plan),'READY'))
 return 'CREATED'

def request(path):
 with transaction(path) as db:
  task,plan,state,n=read(db);plan=json.loads(plan)
  if state in ('WAITING_WORKER','REVIEW','ACCEPTED','DELIVERED','HOLD'):return action_db(db)
  if state not in ('READY','REPAIR_READY'):raise ValueError('REQUEST_STATE')
  if n>=plan['max_attempts']:
   db.execute("UPDATE task SET state='HOLD'");return {'action':'HOLD','reason':'ATTEMPT_BOUND'}
  feedback=None
  if n:feedback=json.loads(db.execute('SELECT review FROM attempts WHERE n=?',(n,)).fetchone()[0])['reason']
  req={'task_id':task,'attempt':n+1,'input_sha256':plan['input_sha256'],'goal':plan['goal'],'feedback':feedback}
  db.execute('INSERT INTO attempts(n,request) VALUES(?,?)',(n+1,canon(req)))
  db.execute("UPDATE task SET state='WAITING_WORKER',attempt=?",(n+1,))
  # Host may execute only this newly returned dispatch, never an uncertain replay.
  return {'action':'DISPATCH_ONCE','request':req}

def bind(path,n,agent,task_id,input_sha256):
 ident(agent)
 with transaction(path) as db:
  response_binding(db,task_id,input_sha256)
  _,_,state,current=read(db)
  if type(n) is not int or n!=current or state!='WAITING_WORKER':raise ValueError('STALE_BIND')
  old=db.execute('SELECT agent FROM attempts WHERE n=?',(n,)).fetchone()[0]
  if old is not None and old!=agent:raise ValueError('AGENT_ALIAS')
  db.execute('UPDATE attempts SET agent=? WHERE n=?',(agent,n))

def response_binding(db,task_id,input_sha256):
 task,plan,_,_=read(db)
 if task_id!=task or input_sha256!=json.loads(plan)["input_sha256"]:raise ValueError("TASK_INPUT_BINDING")

def submit(path,n,agent,text,task_id,input_sha256):
 ident(agent)
 if type(text) is not str or not text.strip() or len(text.encode())>12000:raise ValueError('CANDIDATE_BOUND')
 with transaction(path) as db:
  response_binding(db,task_id,input_sha256)
  _,_,state,current=read(db)
  if type(n) is not int or n!=current:raise ValueError('STALE_CANDIDATE')
  row=db.execute('SELECT agent,candidate,candidate_hash FROM attempts WHERE n=?',(n,)).fetchone()
  if row[0]!=agent:raise ValueError('AGENT_BINDING')
  if row[1] is not None:
   if row[1]!=text or row[2]!=digest(text):raise ValueError('CANDIDATE_ALIAS')
   return 'DUPLICATE'
  if state!='WAITING_WORKER':raise ValueError('SUBMIT_STATE')
  db.execute('UPDATE attempts SET candidate=?,candidate_hash=? WHERE n=?',(text,digest(text),n))
  db.execute("UPDATE task SET state='REVIEW'")
 return 'SUBMITTED'

def review(path,n,candidate_hash,decision,reason,task_id,input_sha256):
 if decision not in ('ACCEPT','REPAIR'):raise ValueError('DECISION')
 ident(reason)
 with transaction(path) as db:
  response_binding(db,task_id,input_sha256)
  _,_,state,current=read(db)
  if type(n) is not int or n!=current:raise ValueError('STALE_REVIEW')
  row=db.execute('SELECT candidate_hash,review FROM attempts WHERE n=?',(n,)).fetchone()
  if row[0] is None or row[0]!=candidate_hash:raise ValueError('REVIEW_BINDING')
  body=canon({'attempt':n,'candidate_sha256':candidate_hash,'decision':decision,'reason':reason,'reviewer':'trusted-host-controller','task_id':task_id,'input_sha256':input_sha256})
  if row[1] is not None:
   if row[1]!=body:raise ValueError('REVIEW_ALIAS')
   return 'DUPLICATE'
  if state!='REVIEW':raise ValueError('REVIEW_STATE')
  db.execute('UPDATE attempts SET review=? WHERE n=?',(body,n))
  db.execute('UPDATE task SET state=?',('ACCEPTED' if decision=='ACCEPT' else 'REPAIR_READY',))
 return decision

def effect_db(db):
 task,plan,state,n=read(db)
 if state not in ('ACCEPTED','DELIVERED'):raise ValueError('NOT_ACCEPTED')
 row=db.execute('SELECT candidate,candidate_hash,review FROM attempts WHERE n=?',(n,)).fetchone()
 review_record=json.loads(row[2]) if row[2] else {}
 if row[0] is None or digest(row[0])!=row[1] or review_record.get('decision')!='ACCEPT' or review_record.get('candidate_sha256')!=row[1] or review_record.get('attempt')!=n or review_record.get('task_id')!=task or review_record.get('input_sha256')!=json.loads(plan)['input_sha256']:raise ValueError('ACCEPTANCE_RECORD')
 return {'effect_id':st.EID(task,'publish','genie-report-inbox'),'transition_id':task,'kind':'publish','target':'genie-report-inbox','payload':row[0],'generation':1,'authority_config':'NONCLAIM-trusted-host-review'}

def action_db(db):
 task,plan,state,n=read(db);out={'task_id':task,'state':state,'attempt':n}
 if state=='WAITING_WORKER':
  row=db.execute('SELECT request,agent FROM attempts WHERE n=?',(n,)).fetchone();out.update(action='RECONCILE_WORKER',request=json.loads(row[0]),agent=row[1],dispatch_uncertain=row[1] is None)
 else:out['action']={'READY':'REQUEST_WORKER','REPAIR_READY':'REQUEST_REPAIR','REVIEW':'REVIEW_CANDIDATE','ACCEPTED':'DELIVER_AND_OBSERVE','DELIVERED':'OBSERVE_DESTINATION','HOLD':'HOLD'}[state]
 return out

def status(path,sink=None):
 with transaction(path,False) as db:
  out=action_db(db)
  if out['state'] in ('ACCEPTED','DELIVERED'):
   try:evidence='UNKNOWN' if sink is None else report_sink.observe(sink,effect_db(db))
   except sqlite3.Error:evidence='UNKNOWN'
   out['destination']=evidence;out['completion']='CONFIRMED' if evidence=='CONFIRMED' else 'UNKNOWN'
 return out

def deliver(path,sink,crash='none'):
 with transaction(path,False) as db:e=effect_db(db)
 result=report_sink.deliver(sink,e,crash)
 observation=report_sink.observe(sink,e)
 if observation!='CONFIRMED':return {'delivery':result,'completion':'UNKNOWN'}
 with transaction(path) as db:
  if effect_db(db)!=e:raise ValueError('DELIVERY_BINDING')
  db.execute("UPDATE task SET state='DELIVERED'")
 return {'delivery':result,'completion':'CONFIRMED'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('database');ap.add_argument('operation',choices=['init','inspect','create','request','bind','submit','review','status','deliver']);ap.add_argument('--sink');ap.add_argument('--crash',choices=['none','after_commit'],default='none');a=ap.parse_args()
 x={} if a.operation in ('init','inspect','request','status','deliver') else json.load(sys.stdin)
 if a.operation=='init':initialize(a.database);out={'status':'INITIALIZED'}
 elif a.operation=='inspect':out=inspect(a.database)
 elif a.operation=='create':out=create(a.database,x)
 elif a.operation=='request':out=request(a.database)
 elif a.operation=='bind':bind(a.database,**x);out='BOUND'
 elif a.operation=='submit':out=submit(a.database,**x)
 elif a.operation=='review':out=review(a.database,**x)
 elif a.operation=='status':out=status(a.database,a.sink)
 else:out=deliver(a.database,a.sink,a.crash)
 print(canon(out))
if __name__=='__main__':main()

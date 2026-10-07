"""Owned local report inbox. Deduplication is atomic with the concrete report row."""
import argparse,hashlib,json,os,sqlite3
from pathlib import Path
FIELDS={'effect_id','transition_id','kind','target','payload','generation','authority_config'}

def canonical(e):return json.dumps(e,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def valid(e):
 if type(e) is not dict or set(e)!=FIELDS:raise ValueError('EFFECT_FIELDS')
 if type(e['generation']) is not int or e['generation']!=1:raise ValueError('ONE_TASK_GENERATION')
 if any(type(e[k]) is not str or not e[k] or e[k]!=e[k].strip() for k in FIELDS-{'generation','payload'}):raise ValueError('EXACT_IDENTITIES')
 if type(e['payload']) is not str or not e['payload'] or len(e['payload'].encode())>16384:raise ValueError('BOUNDED_PAYLOAD')
 if e['kind']!='publish' or e['target']!='genie-report-inbox':raise ValueError('FIXED_DESTINATION')
 import stateful_subject as st
 if e['effect_id']!=st.EID(e['transition_id'],e['kind'],e['target']):raise ValueError('EFFECT_ID_BINDING')
 return canonical(e)

def deliver(path,e,crash='none'):
 body=valid(e);db=sqlite3.connect(path,timeout=5,isolation_level=None)
 try:
  db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA foreign_keys=ON')
  db.executescript('CREATE TABLE IF NOT EXISTS reports(effect_id TEXT PRIMARY KEY,target TEXT NOT NULL UNIQUE,body TEXT NOT NULL,payload_sha256 TEXT NOT NULL); CREATE TABLE IF NOT EXISTS applications(effect_id TEXT PRIMARY KEY REFERENCES reports(effect_id),applied_body TEXT NOT NULL);')
  db.execute('BEGIN IMMEDIATE')
  old=db.execute('SELECT body FROM reports WHERE effect_id=?',(e['effect_id'],)).fetchone()
  if old:
   if old[0]!=body:raise ValueError('ID_REUSE_MISMATCH')
   applied=db.execute('SELECT applied_body FROM applications WHERE effect_id=?',(e['effect_id'],)).fetchone()
   if applied!=(body,):raise ValueError('INCOMPLETE_EXISTING_APPLICATION')
   db.execute('COMMIT');return 'DUPLICATE'
  db.execute('INSERT INTO reports VALUES(?,?,?,?)',(e['effect_id'],e['target'],body,hashlib.sha256(e['payload'].encode()).hexdigest()))
  db.execute('INSERT INTO applications VALUES(?,?)',(e['effect_id'],body))
  if crash=='before_commit':os._exit(72)
  db.execute('COMMIT')
  if crash=='after_commit':os._exit(73)
  return 'APPLIED'
 except BaseException:
  if db.in_transaction:db.execute('ROLLBACK')
  raise
 finally:db.close()

def observe(path,e):
 body=valid(e)
 if not Path(path).is_file():return 'UNKNOWN'
 db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5,isolation_level=None)
 try:
  db.execute('BEGIN')
  row=db.execute('SELECT body,payload_sha256 FROM reports WHERE effect_id=?',(e['effect_id'],)).fetchone();app=db.execute('SELECT applied_body FROM applications WHERE effect_id=?',(e['effect_id'],)).fetchone()
  count=db.execute('SELECT count(*) FROM reports').fetchone()[0];acount=db.execute('SELECT count(*) FROM applications').fetchone()[0]
  if row is None or app is None:return 'UNKNOWN'
  if row!=(body,hashlib.sha256(e['payload'].encode()).hexdigest()) or app!=(body,) or count!=1 or acount!=1:return 'MISMATCH'
  return 'CONFIRMED'
 except sqlite3.Error:return 'UNKNOWN'
 finally:db.close()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('database');ap.add_argument('--crash',choices=['none','before_commit','after_commit'],default='none');a=ap.parse_args()
 import sys
 try:r=deliver(a.database,json.loads(sys.stdin.read()),a.crash);print(json.dumps({'delivery':r}));return 0
 except (ValueError,sqlite3.Error) as e:print(json.dumps({'delivery':'REJECT','reason':str(e)}));return 2
if __name__=='__main__':raise SystemExit(main())

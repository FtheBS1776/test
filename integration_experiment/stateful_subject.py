import sqlite3,json,hashlib
def S(x): return type(x) is str and bool(x) and x==x.strip()
def I(x): return type(x) is int and x>=0
def H(parts):
 if not all(S(x) for x in parts): raise ValueError("BAD_ID")
 return hashlib.sha256(json.dumps(parts,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def EID(tid,kind,target): return H(["effect-v1",tid,kind,target])
def connect(p):
 c=sqlite3.connect(p,timeout=10,isolation_level=None,check_same_thread=False)
 c.execute("PRAGMA journal_mode=WAL");c.execute("PRAGMA synchronous=FULL")
 c.executescript("""
 CREATE TABLE IF NOT EXISTS head(id INTEGER PRIMARY KEY CHECK(id=1),gen INTEGER NOT NULL,digest TEXT NOT NULL,config TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS tx(tid TEXT PRIMARY KEY,fp TEXT NOT NULL,gen INTEGER NOT NULL,digest TEXT NOT NULL,config TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS outbox(eid TEXT PRIMARY KEY,tid TEXT NOT NULL,kind TEXT NOT NULL,target TEXT NOT NULL,payload TEXT NOT NULL,gen INTEGER NOT NULL,config TEXT NOT NULL,ack_receipt TEXT);
 CREATE TABLE IF NOT EXISTS projection(target TEXT PRIMARY KEY,lineage TEXT NOT NULL,gen INTEGER NOT NULL,tid TEXT NOT NULL,config TEXT NOT NULL,payload TEXT NOT NULL);
 """); return c
def init(c):c.execute("insert or ignore into head values(1,0,'A','C')")
def FP(pg,pd,succ,tid,cfg,effects):return H(["tx-v1",str(pg),pd,succ,tid,cfg,json.dumps(effects,separators=(",",":"))])
def activate(c,pg,pd,succ,tid,cfg,effects=(),hook=None):
 if not I(pg) or not all(S(x) for x in (pd,succ,tid,cfg)):return ("REJECT",None)
 if type(effects) not in (tuple,list): return ("REJECT",None)
 for effect in effects:
  if type(effect) is not tuple or len(effect)!=3 or not all(S(x) for x in effect): return ("REJECT",None)
 f=FP(pg,pd,succ,tid,cfg,effects)
 c.execute("BEGIN IMMEDIATE")
 try:
  old=c.execute("select fp,gen,digest,config from tx where tid=?",(tid,)).fetchone()
  if old:
   c.execute("COMMIT");return ("OK",old[1:]) if old[0]==f else ("ID_REUSE_MISMATCH",None)
  if c.execute("select gen,digest,config from head where id=1").fetchone()!=(pg,pd,cfg):
   c.execute("ROLLBACK");return ("STALE",None)
  if hook:hook("before_write")
  ng=pg+1;c.execute("update head set gen=?,digest=? where id=1",(ng,succ))
  c.execute("insert into tx values(?,?,?,?,?)",(tid,f,ng,succ,cfg))
  seen=set()
  for kind,target,payload in effects:
   if not all(S(x) for x in (kind,target,payload)):raise ValueError("BAD_EFFECT")
   x=EID(tid,kind,target)
   if x in seen:raise ValueError("DUP_EFFECT")
   seen.add(x);c.execute("insert into outbox values(?,?,?,?,?,?,?,NULL)",(x,tid,kind,target,payload,ng,cfg))
  if hook:hook("before_commit")
  c.execute("COMMIT")
  if hook:hook("after_commit")
  return ("OK",(ng,succ,cfg))
 except:
  try:c.execute("ROLLBACK")
  except:pass
  raise
class Receipt:
 __slots__=("eid","payload_digest","provider","_sealed")
 def __init__(self,e,p,provider):
  if not all(S(x) for x in (e,p,provider)):raise ValueError
  object.__setattr__(self,"eid",e);object.__setattr__(self,"payload_digest",p);object.__setattr__(self,"provider",provider);object.__setattr__(self,"_sealed",True)
 def __setattr__(self,n,v):
  if getattr(self,"_sealed",False):raise AttributeError("sealed")
  object.__setattr__(self,n,v)
class Verifier:
 __slots__=("provider","_sealed")
 def __init__(self,p):
  if not S(p):raise ValueError
  object.__setattr__(self,"provider",p);object.__setattr__(self,"_sealed",True)
 def __setattr__(self,n,v):
  if getattr(self,"_sealed",False):raise AttributeError("sealed")
  object.__setattr__(self,n,v)
 def verify(self,c,r):
  if type(r) is not Receipt or r.provider!=self.provider:return False
  row=c.execute("select payload from outbox where eid=?",(r.eid,)).fetchone()
  return bool(row) and hashlib.sha256(row[0].encode()).hexdigest()==r.payload_digest
def ack(c,r,v):
 if type(v) is not Verifier or not Verifier.verify(v,c,r):return "REJECT"
 c.execute("update outbox set ack_receipt=? where eid=?",(r.payload_digest,r.eid));return "ACK"
def apply(c,eid,lineage="L"):
 if not S(eid) or not S(lineage): return "REJECT"
 c.execute("BEGIN IMMEDIATE")
 try:
  row=c.execute("select tid,target,payload,gen,config from outbox where eid=?",(eid,)).fetchone()
  if not row:
   c.execute("ROLLBACK"); return "MISSING"
  tid,target,payload,gen,cfg=row
  old=c.execute("select lineage,gen,tid,config,payload from projection where target=?",(target,)).fetchone()
  if old:
   ol,og,ot,oc,op=old
   if ol!=lineage or oc!=cfg:
    c.execute("ROLLBACK"); return "IDENTITY_MISMATCH"
   if gen<og:
    c.execute("ROLLBACK"); return "STALE"
   if gen==og:
    c.execute("ROLLBACK"); return "IDEMPOTENT" if (tid,payload)==(ot,op) else "CONFLICT"
   if gen!=og+1:
    c.execute("ROLLBACK"); return "GAP"
  elif gen!=1:
   c.execute("ROLLBACK"); return "GAP"
  c.execute("insert or replace into projection values(?,?,?,?,?,?)",(target,lineage,gen,tid,cfg,payload))
  c.execute("COMMIT"); return "APPLIED"
 except:
  try:c.execute("ROLLBACK")
  except:pass
  raise
def coherent(c,targets):
 if type(targets) not in (list,tuple) or not targets or not all(S(x) for x in targets) or len(set(targets))!=len(targets):return "REJECT"
 q="select lineage,gen,tid,config from projection where target in (%s)"%(",".join("?"*len(targets)))
 rows=c.execute(q,targets).fetchall()
 if len(rows)!=len(targets):return "INCOMPLETE"
 return "COHERENT" if len(set(rows))==1 else "MIXED"

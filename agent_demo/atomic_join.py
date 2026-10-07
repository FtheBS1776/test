import hashlib
import stateful_subject as st
from execution_identity_reference import SignedEnvelope,ExecutionIdentityVerifier
from lifecycle_registry import RegistrySnapshot

def ensure_authority_schema(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS lifecycle_current(
      id INTEGER PRIMARY KEY CHECK(id=1),
      generation INTEGER NOT NULL,
      config TEXT NOT NULL,
      registry_digest TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS registry_snapshots(
      digest TEXT PRIMARY KEY,
      config TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS execution_consumption(
      execution_id TEXT PRIMARY KEY,
      envelope_fp TEXT NOT NULL,
      tid TEXT NOT NULL UNIQUE
    );
    """)

class BoundRegistryStore:
    __slots__=("_snapshots",)
    def __init__(self,snapshots):
        if type(snapshots) is not tuple: raise ValueError("BAD_SNAPSHOTS")
        d={}
        for s in snapshots:
            if type(s) is not RegistrySnapshot: raise ValueError("BAD_SNAPSHOT")
            if s.digest in d: raise ValueError("DUP_SNAPSHOT")
            d[s.digest]=s
        self._snapshots=d
    def exact(self,digest,config):
        s=self._snapshots.get(digest)
        return s if s is not None and s.config==config and s.digest==digest else None

def provision_genesis(c,generation,config,snapshot):
    ensure_authority_schema(c)
    if type(generation) is not int or generation!=0 or type(snapshot) is not RegistrySnapshot:
        raise ValueError("BAD_GENESIS")
    if snapshot.config!=config: raise ValueError("BAD_GENESIS")
    c.execute("BEGIN IMMEDIATE")
    try:
        if c.execute("select count(*) from lifecycle_current").fetchone()[0]: raise ValueError("ALREADY_PROVISIONED")
        c.execute("insert into registry_snapshots values(?,?)",(snapshot.digest,config))
        c.execute("insert into lifecycle_current values(1,?,?,?)",(0,config,snapshot.digest))
        c.execute("update head set config=? where id=1",(config,))
        c.execute("COMMIT")
    except Exception:
        if c.in_transaction:c.execute("ROLLBACK")
        raise

def rotate_lifecycle(c,old_generation,old_config,old_digest,new_generation,new_snapshot,
                     incumbent_authorized,successor_authorized):
    # Authorization booleans model outputs of inherited Pass-192 root verifier, not caller authority.
    if type(new_snapshot) is not RegistrySnapshot: return "REJECT"
    if incumbent_authorized is not True or successor_authorized is not True:return "REJECT"
    c.execute("BEGIN IMMEDIATE")
    try:
        cur=c.execute("select generation,config,registry_digest from lifecycle_current where id=1").fetchone()
        if cur!=(old_generation,old_config,old_digest):c.execute("ROLLBACK");return "STALE"
        if type(new_generation) is not int or new_generation!=old_generation+1:
            c.execute("ROLLBACK");return "REJECT"
        c.execute("insert or ignore into registry_snapshots values(?,?)",(new_snapshot.digest,new_snapshot.config))
        c.execute("update lifecycle_current set generation=?,config=?,registry_digest=? where id=1",
                  (new_generation,new_snapshot.config,new_snapshot.digest))
        c.execute("update head set config=? where id=1",(new_snapshot.config,))
        c.execute("COMMIT");return "OK"
    except Exception:
        if c.in_transaction:c.execute("ROLLBACK")
        raise

def activate_bound(c,store,signed,pg,pd,succ,tid,effects=(),hook=None):
    if type(store) is not BoundRegistryStore or type(signed) is not SignedEnvelope:return ("REJECT",None)
    if not st.I(pg) or not all(st.S(x) for x in (pd,succ,tid)):return ("REJECT",None)
    if type(effects) not in (tuple,list):return ("REJECT",None)
    for e in effects:
        if type(e) is not tuple or len(e)!=3 or not all(st.S(x) for x in e):return ("REJECT",None)
    ensure_authority_schema(c)
    c.execute("BEGIN IMMEDIATE")
    try:
        life=c.execute("select generation,config,registry_digest from lifecycle_current where id=1").fetchone()
        if life is None:c.execute("ROLLBACK");return ("AUTHORITY_UNPROVISIONED",None)
        lg,cfg,rd=life
        snap=store.exact(rd,cfg)
        if snap is None:c.execute("ROLLBACK");return ("REGISTRY_BINDING_UNAVAILABLE",None)
        try:
            env=snap.verifier().verify(signed)
        except Exception:
            c.execute("ROLLBACK");return ("REJECT",None)
        if env.authority_config!=cfg:c.execute("ROLLBACK");return ("AUTHORITY_CONFIG_MISMATCH",None)
        efp=hashlib.sha256(env.canonical()).hexdigest()
        prior=c.execute("select envelope_fp,tid from execution_consumption where execution_id=?",
                        (env.execution_id,)).fetchone()
        f=st.FP(pg,pd,succ,tid,cfg,effects)
        tx=c.execute("select fp,gen,digest,config from tx where tid=?",(tid,)).fetchone()
        if prior or tx:
            if prior==(efp,tid) and tx and tx[0]==f:
                c.execute("COMMIT");return ("OK",tx[1:])
            c.execute("ROLLBACK");return ("EXECUTION_OR_TRANSITION_REUSE_MISMATCH",None)
        if c.execute("select gen,digest,config from head where id=1").fetchone()!=(pg,pd,cfg):
            c.execute("ROLLBACK");return ("STALE",None)
        if hook:hook("inside_transaction",lg,cfg,rd)
        ng=pg+1
        c.execute("update head set gen=?,digest=? where id=1",(ng,succ))
        c.execute("insert into tx values(?,?,?,?,?)",(tid,f,ng,succ,cfg))
        c.execute("insert into execution_consumption values(?,?,?)",(env.execution_id,efp,tid))
        seen=set()
        for kind,target,payload in effects:
            x=st.EID(tid,kind,target)
            if x in seen:raise ValueError("DUP_EFFECT")
            seen.add(x)
            c.execute("insert into outbox(eid,tid,kind,target,payload,gen,config) values(?,?,?,?,?,?,?)",
                      (x,tid,kind,target,payload,ng,cfg))
        c.execute("COMMIT");return ("OK",(ng,succ,cfg))
    except Exception:
        if c.in_transaction:c.execute("ROLLBACK")
        raise

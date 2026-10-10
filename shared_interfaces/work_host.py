"""Mutating current-host entry; no model calls, restart or safe retry."""
import argparse,hashlib,json,sys,types
from pathlib import Path
PINS={'cli.py':'c0a35e699cc4ad2fd2e176fd8ab951fbab7f57f56c783230925d078b38ff8af4','session_driver.py':'89b0fd1ef48d5460dada5cc59b25072a10ec9b5c7049af25eabbb2d4464bf9d9'}
def _load(name):
    folder=next(p for p in Path(__file__).resolve().parents if p.name=='shared_interfaces')
    source=folder/name
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINS[name]:raise ValueError('SOURCE_BINDING')
    module=types.ModuleType('_host_'+name[:-3]);module.__file__=str(source)
    exec(compile(raw,str(source),'exec'),module.__dict__)
    return module
class _Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('ARGUMENTS')
class _Once(argparse.Action):
    def __call__(self,parser,namespace,value,option_string=None):
        if self.dest in getattr(namespace,'_seen',set()):raise ValueError('ARGUMENTS')
        seen=getattr(namespace,'_seen',set());seen.add(self.dest);namespace._seen=seen
        setattr(namespace,self.dest,value)
def _emit(result):
    try:print(json.dumps({'kind':'terminal','result':result},separators=(',',':')))
    except Exception:pass

def main(argv=None):
    try:
        p=_Parser(add_help=False,allow_abbrev=False)
        p.add_argument('--registry',required=True,action=_Once)
        p.add_argument('--run',required=True,action=_Once)
        p.add_argument('--max-actions',type=int,default=64,action=_Once)
        a=p.parse_args(argv)
        if not 1<=a.max_actions<=128:raise ValueError('BOUND')
        runs=_load('cli.py')._read_registry(a.registry)
        if a.run not in runs:raise ValueError('ALIAS')
        driver=_load('session_driver.py')
    except Exception:
        _emit({'action':'REJECT','reason':'HOST_ENTRY_REJECT'});return 2
    try:
        result=driver.serve_run(runs,a.run,max_actions=a.max_actions)
        action=result.get('action')
        if action=='UNKNOWN':return 3
        if action=='REJECT':return 2
        return 0 if action=='STOP' and result.get('reason')=='ALL_TASKS_COMPLETE' else 4
    except Exception:
        _emit({'action':'UNKNOWN','reason':'HOST_ENTRY_UNKNOWN','preserve':True,'allow_new_invocation':False})
        return 3
if __name__=='__main__':sys.exit(main())

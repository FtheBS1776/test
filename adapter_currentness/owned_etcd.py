"""Utilities for explicitly owned disposable loopback etcd processes only."""
from pathlib import Path
import contextlib,hashlib,json,os,platform,socket,subprocess,tempfile,time
ROOT=Path(__file__).resolve().parent
PINS={'etcd':'030b4b2efd1bcc9ab043080c35f7bb68551e962b23efe62e2f2713429bd9e0f2','etcdctl':'18416269c49d0f25624938b0b45d5bd5d3eb980ab92048dc4652c66a4246141e'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'))
def demand(v,label):
    if not v:raise RuntimeError(label)
def seal(out,status):
    save(out/'STATUS.json',status)
    save(out/'EVIDENCE_MANIFEST.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='EVIDENCE_MANIFEST.json'})
class OwnedCluster:
    def __init__(self,out,n):
        self.out=out;self.n=n;self.processes={};self.logs=[];self.counts={};self.events=[]
        self.env={k:v for k,v in os.environ.items() if not k.startswith(('ETCD_','ETCDCTL_'))}
    def event(self,**e):
        e['monotonic_ns']=time.monotonic_ns();self.events.append(e);save(self.out/'PROCESS_EVENTS.json',self.events)
    def __enter__(self):
        self.stack=contextlib.ExitStack()
        try:
            for n,h in PINS.items():demand(sha(ROOT/'runtime'/n)==h,'binary identity '+n)
            save(self.out/'IDENTITY.json',{'binary_sha256':PINS,'platform':platform.platform(),'python':platform.python_version(),'execution_class':'LOCAL_DISPOSABLE_REAL_ETCD','sources':{p.name:sha(p) for p in ROOT.glob('*.py')}})
            for p in ROOT.glob('*.py'):(self.out/p.name).write_bytes(p.read_bytes())
            self.work=Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='brains10-fault-')))
            self.stack.callback(self.close)
            reserved=[]
            for _ in range(2*self.n):
                s=socket.socket();s.bind(('127.0.0.1',0));reserved.append(s)
            ports=[s.getsockname()[1] for s in reserved]
            self.endpoints=[f'http://127.0.0.1:{ports[2*i]}' for i in range(self.n)]
            peers=[f'http://127.0.0.1:{ports[2*i+1]}' for i in range(self.n)]
            self.initial=','.join(f'm{i}={peers[i]}' for i in range(self.n));self.argv=[]
            for s in reserved:s.close()
            for i in range(self.n):
                self.argv.append([str(ROOT/'runtime/etcd'),'--name',f'm{i}','--data-dir',str(self.work/f'm{i}'),'--listen-client-urls',self.endpoints[i],'--advertise-client-urls',self.endpoints[i],'--listen-peer-urls',peers[i],'--initial-advertise-peer-urls',peers[i],'--initial-cluster',self.initial,'--initial-cluster-token',self.work.name,'--initial-cluster-state','new'])
            save(self.out/'CONFIGURATION.json',{'endpoints':self.endpoints,'peers':peers,'initial_cluster':self.initial,'namespace':'/brains10/fault/'+self.work.name,'members':self.n,'tls':False})
            save(self.out/'SERVER_COMMANDS.json',self.argv)
            for i in range(self.n):self.start(i)
            self.wait_healthy(range(self.n),'startup')
            return self
        except BaseException:self.stack.close();raise
    def __exit__(self,*exc):self.stack.close()
    def start(self,i):
        demand(i not in self.processes or self.processes[i].poll() is not None,'member still running')
        count=self.counts.get(i,0);self.counts[i]=count+1
        log=(self.out/f'SERVER_{i}_START_{count}.txt').open('wb');self.logs.append(log)
        p=subprocess.Popen(self.argv[i],stdout=log,stderr=subprocess.STDOUT,env=self.env);self.processes[i]=p
        self.event(action='start',member_index=i,pid=p.pid,start_number=count,unchanged_data_directory=str(self.work/f'm{i}'))
    def stop(self,i,crash=False):
        p=self.processes[i];demand(p.poll() is None,'member already exited')
        self.event(action='SIGKILL' if crash else 'SIGTERM',member_index=i,pid=p.pid)
        if crash:p.kill()
        else:p.terminate()
        try:p.wait(timeout=6)
        except subprocess.TimeoutExpired:p.kill();p.wait();self.event(action='cleanup_forced',member_index=i,pid=p.pid)
        self.event(action='exit',member_index=i,pid=p.pid,returncode=p.returncode)
    def close(self):
        for i,p in self.processes.items():
            if p.poll() is None:self.stop(i)
        for f in self.logs:f.close()
    def ctl(self,label,i,args,stdin=None,checked=True):
        argv=[str(ROOT/'runtime/etcdctl'),'--endpoints='+self.endpoints[i],'--command-timeout=2s','--dial-timeout=1s','--write-out=json']+args
        start=time.monotonic_ns()
        try:
            r=subprocess.run(argv,input=stdin,text=True,capture_output=True,timeout=5,env=self.env)
            rec={'argv':argv,'stdin':stdin,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
        except subprocess.TimeoutExpired as e:rec={'argv':argv,'stdin':stdin,'returncode':124,'stdout':str(e.stdout),'stderr':str(e.stderr),'harness_timeout':True}
        rec.update(start_monotonic_ns=start,end_monotonic_ns=time.monotonic_ns());save(self.out/(label+'.json'),rec)
        if checked:demand(rec['returncode']==0,'command failed '+label)
        return rec
    def wait_healthy(self,indices,stage):
        indices=list(indices)
        for attempt in range(12):
            outcomes=[self.ctl(f'{stage}_health_{attempt}_{i}',i,['endpoint','health'],checked=False)['returncode']==0 for i in indices]
            if all(outcomes):return
            demand(all(self.processes[i].poll() is None for i in indices),'owned member exited')
            time.sleep(.15)
        raise RuntimeError('bounded readiness exhausted '+stage)

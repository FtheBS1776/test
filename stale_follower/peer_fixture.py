"""Peer-only relay fault inside three exclusively owned loopback etcd processes."""
import contextlib,hashlib,json,os,platform,select,socket,tempfile,threading,time
from pathlib import Path
from owned_etcd import OwnedCluster,PINS,ROOT,demand,save,sha
class PeerNetwork:
    def __init__(self,out,backends):
        demand(len(backends)==3 and all(host=='127.0.0.1' and 0<port<65536 for host,port in backends),'FIXED_OWNED_BACKENDS')
        self.out=out;self.backends=backends;self.lock=threading.RLock();self.stop=threading.Event();self.active={};self.events=[];self.threads=[];self.listeners=[];self.ids=None;self.isolated=None;self.isolated_index=None;self.sequence=0;self.overflow=False
        for index in range(3):
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(32);listener.settimeout(.2);self.listeners.append(listener)
            t=threading.Thread(target=self.accept,args=(index,listener),daemon=True);self.threads.append(t);t.start()
    def event(self,event,**data):
        with self.lock:
            if len(self.events)>=10000:self.overflow=True;return
            self.events.append({'event':event,'monotonic_ns':time.monotonic_ns(),**data})
    def accept(self,index,listener):
        while not self.stop.is_set():
            try:client,_=listener.accept()
            except socket.timeout:continue
            except OSError:break
            with self.lock:
                if len(self.active)>=64:client.close();self.event('capacity_rejected',destination=index);continue
                cid=self.sequence;self.sequence+=1;self.active[cid]={'client':client,'upstream':None,'destination':index,'source':None}
                t=threading.Thread(target=self.forward,args=(cid,),daemon=True);self.threads.append(t);t.start()
    def denied(self,index,source):
        return self.isolated is not None and (index==self.isolated_index or source==self.isolated or source not in self.ids)
    @staticmethod
    def shutdown(sock):
        if sock is None:return
        try:sock.shutdown(socket.SHUT_RDWR)
        except OSError:pass
        try:sock.close()
        except OSError:pass
    def forward(self,cid):
        upstream=None;source=None;index=None
        try:
            with self.lock:entry=self.active[cid];client=entry['client'];index=entry['destination']
            client.settimeout(3);data=b''
            while b'\r\n\r\n' not in data:
                chunk=client.recv(4096)
                if not chunk:return
                data+=chunk;demand(len(data)<=65536,'PEER_HEADER_LIMIT')
            headers=data.split(b'\r\n\r\n',1)[0].split(b'\r\n')[1:]
            values=[line.split(b':',1)[1].strip().decode('ascii').lower() for line in headers if line.split(b':',1)[0].lower()==b'x-server-from']
            demand(len(values)<=1,'DUPLICATE_MEMBER_HEADER');source=values[0] if values else None
            with self.lock:
                entry['source']=source
                if self.stop.is_set() or self.denied(index,source):self.event('blocked',connection=cid,destination=index,source=source);return
                upstream=socket.create_connection(self.backends[index],timeout=2);entry['upstream']=upstream
                upstream.sendall(data);client.settimeout(2);upstream.settimeout(2)
                self.event('connected',connection=cid,destination=index,source=source)
            while not self.stop.is_set():
                with self.lock:
                    if self.denied(index,source):break
                readable,_,_=select.select([client,upstream],[],[],.2)
                for src in readable:
                    chunk=src.recv(65536)
                    if not chunk:return
                    with self.lock:
                        if self.denied(index,source):return
                        (upstream if src is client else client).sendall(chunk)
        except (OSError,ValueError,RuntimeError) as e:self.event('connection_end',connection=cid,destination=index,source=source,reason=type(e).__name__)
        finally:
            with self.lock:
                entry=self.active.pop(cid,None)
                if entry:self.shutdown(entry['client']);self.shutdown(entry['upstream'])
                self.event('closed',connection=cid,destination=index,source=source)
    def isolate(self,index,ids):
        with self.lock:
            self.ids=[format(value,'x') for value in ids];self.isolated=self.ids[index];self.isolated_index=index
            closed=[]
            for cid,entry in list(self.active.items()):
                if self.denied(entry['destination'],entry['source']):
                    self.shutdown(entry['client']);self.shutdown(entry['upstream']);closed.append(cid)
            self.event('isolate',member_index=index,member_ids_hex=self.ids,closed_connections=closed)
            demand(bool(closed),'NO_EXISTING_CONNECTIONS_ISOLATED')
    def heal(self):
        with self.lock:self.event('heal',member_index=self.isolated_index);self.isolated=None;self.isolated_index=None
    def close(self):
        self.stop.set()
        for listener in self.listeners:self.shutdown(listener)
        with self.lock:
            for entry in list(self.active.values()):self.shutdown(entry['client']);self.shutdown(entry['upstream'])
        deadline=time.monotonic()+8
        # Accept loops are listed before their workers; joining them prevents new workers.
        for thread in list(self.threads):thread.join(timeout=max(0,deadline-time.monotonic()))
        remaining=[thread for thread in self.threads if thread.is_alive()]
        self.event('relay_cleanup',active_connections=len(self.active),live_threads=len(remaining),overflow=self.overflow)
        save(self.out/'PEER_EVENTS.json',self.events)
        demand(not remaining and not self.active and not self.overflow,'RELAY_CLEANUP_INCOMPLETE')
class PeerFixture(OwnedCluster):
    def __init__(self,out):super().__init__(out,3)
    def __enter__(self):
        self.stack=contextlib.ExitStack()
        try:
            for name,digest in PINS.items():demand(sha(ROOT/'runtime'/name)==digest,'BINARY_'+name)
            save(self.out/'IDENTITY.json',{'binary_sha256':PINS,'platform':platform.platform(),'python':platform.python_version(),'execution_class':'OWNED_THREE_MEMBER_LOOPBACK_PEER_FAULT','sources':{p.name:sha(p) for p in ROOT.glob('*.py')}})
            for p in ROOT.glob('*.py'):(self.out/p.name).write_bytes(p.read_bytes())
            self.work=Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='brains10-stale-')))
            reserved=[]
            for _ in range(6):
                sock=socket.socket();sock.bind(('127.0.0.1',0));reserved.append(sock)
            ports=[sock.getsockname()[1] for sock in reserved]
            self.endpoints=[f'http://127.0.0.1:{ports[2*i]}' for i in range(3)];backends=[('127.0.0.1',ports[2*i+1]) for i in range(3)]
            self.network=PeerNetwork(self.out,backends);self.stack.callback(self.network.close);self.stack.callback(self.close)
            peers=[f'http://127.0.0.1:{sock.getsockname()[1]}' for sock in self.network.listeners]
            self.initial=','.join(f'm{i}={peers[i]}' for i in range(3));self.argv=[]
            for sock in reserved:sock.close()
            for i in range(3):
                self.argv.append([str(ROOT/'runtime/etcd'),'--name',f'm{i}','--data-dir',str(self.work/f'm{i}'),'--listen-client-urls',self.endpoints[i],'--advertise-client-urls',self.endpoints[i],'--listen-peer-urls',f'http://127.0.0.1:{backends[i][1]}','--initial-advertise-peer-urls',peers[i],'--initial-cluster',self.initial,'--initial-cluster-token',self.work.name,'--initial-cluster-state','new'])
            save(self.out/'CONFIGURATION.json',{'endpoints':self.endpoints,'advertised_peers':peers,'peer_backends':backends,'initial_cluster':self.initial,'members':3,'tls':False})
            save(self.out/'SERVER_COMMANDS.json',self.argv)
            for i in range(3):self.start(i)
            self.wait_healthy(range(3),'startup');return self
        except BaseException:self.stack.close();raise
    def __exit__(self,*exc):self.stack.close()

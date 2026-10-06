"""Bounded fixed-upstream relay for one owned loopback adapter namespace."""
import base64,http.client,http.server,json,threading,time
from urllib.parse import urlsplit
from owned_etcd import demand,save
class TransportFixture:
    def __init__(self,out,label,upstream,prefix):
        u=urlsplit(upstream);demand(u.scheme=='http' and u.hostname=='127.0.0.1' and u.port,'OWNED_UPSTREAM')
        self.out=out;self.label=label;self.port=u.port;self.prefix=prefix.encode()+b'/';self.lock=threading.RLock();self.events=[];self.errors=[];self.active=0;self.count=0;self.armed=False;self.accepted=threading.Event();self.release=threading.Event();self.completed=threading.Event()
    def event(self,event,**values):
        with self.lock:self.events.append({'event':event,'monotonic_ns':time.monotonic_ns(),**values})
    def arm(self):
        with self.lock:demand(not self.armed and not self.accepted.is_set(),'ARM_ONCE');self.armed=True;self.event('arm')
    def __enter__(self):
        fixture=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                self.connection.settimeout(3);held=False;index=None
                with fixture.lock:fixture.active+=1;fixture.count+=1;index=fixture.count
                try:
                    demand(index<=32,'REQUEST_CAP');n=int(self.headers.get('Content-Length','0'));demand(0<n<65536 and self.path in ['/v3/kv/range','/v3/kv/txn'],'SELECTED_ROUTES');body=self.rfile.read(n);demand(len(body)==n,'FULL_BODY');obj=json.loads(body)
                    if self.path=='/v3/kv/range':
                        demand(set(obj)=={'key','serializable'} and obj['serializable'] is False,'NORMAL_RANGE_ONLY');keys=[obj['key']]
                    else:
                        demand(set(obj)=={'compare','success','failure'} and len(obj['compare'])==5 and len(obj['success'])==4 and obj['failure']==[],'BOUNDED_ACTIVATION_ONLY');keys=[v['key'] for v in obj['compare']]+[v['requestPut']['key'] for v in obj['success']]
                    demand(all(base64.b64decode(k,validate=True).startswith(fixture.prefix) for k in keys),'EXACT_OWNED_NAMESPACE')
                    with fixture.lock:
                        if self.path=='/v3/kv/txn' and fixture.armed:fixture.armed=False;held=True
                    fixture.event('accepted',request_index=index,path=self.path,body=body.decode(),held=held)
                    if held:fixture.accepted.set();demand(fixture.release.wait(10),'HOLD_BOUND')
                    fixture.event('forward',request_index=index,held=held)
                    conn=http.client.HTTPConnection('127.0.0.1',fixture.port,timeout=3)
                    try:
                        conn.request('POST',self.path,body,{'Content-Type':'application/json'});response=conn.getresponse();raw=response.read(65537);code=response.status;demand(len(raw)<=65536 and code==200,'UPSTREAM_SCOPE')
                    finally:conn.close()
                    fixture.event('upstream_complete',request_index=index,held=held,response=raw.decode(),http_status=code)
                    if held:fixture.event('late_response_not_delivered',request_index=index);fixture.completed.set()
                    else:self.send_response(code);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
                except Exception as e:
                    with fixture.lock:fixture.errors.append(type(e).__name__+': '+str(e))
                    fixture.event('handler_error',request_index=index,error=type(e).__name__+': '+str(e))
                finally:
                    with fixture.lock:fixture.active-=1
                    self.close_connection=True
        class Server(http.server.ThreadingHTTPServer):daemon_threads=False;block_on_close=True
        self.server=Server(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=lambda:self.server.serve_forever(poll_interval=.05),daemon=True);self.thread.start()
        save(self.out/(self.label+'_TRANSPORT_CONFIG.json'),{'endpoint':self.address,'upstream':'http://127.0.0.1:'+str(self.port),'namespace_prefix':self.prefix.decode(),'max_requests':32,'max_request_bytes':65535,'socket_seconds':3,'hold_seconds':10,'witness_used_for_reconciliation':False})
        return self
    @property
    def address(self):return 'http://127.0.0.1:'+str(self.server.server_port)
    def resume(self):self.event('release');self.release.set()
    def __exit__(self,*exc):
        self.release.set();self.server.shutdown();self.thread.join(timeout=4);self.server.server_close();self.event('cleanup',active_workers=self.active,server_thread_alive=self.thread.is_alive(),errors=self.errors);save(self.out/(self.label+'_TRANSPORT_EVENTS.json'),self.events);demand(not self.active and not self.thread.is_alive() and not self.errors,'TRANSPORT_CLEANUP')

"""Three fixed database schedules on an owned single-member loopback fixture."""
import argparse,base64,http.client,http.server,json,os,threading,time
from pathlib import Path
from urllib.parse import urlsplit
from owned_etcd import OwnedCluster,canonical,demand,save,seal
from gate_inputs import build_init_script
ROOT=Path(__file__).resolve().parent
def b64(s):return base64.b64encode(s.encode()).decode()
def rpc(endpoint,path,body,timeout=4):
    url=urlsplit(endpoint);demand(url.hostname=='127.0.0.1' and url.scheme=='http','ONLY_OWNED_LOOPBACK')
    conn=http.client.HTTPConnection('127.0.0.1',url.port,timeout=timeout)
    try:
        conn.request('POST',path,body,{'Content-Type':'application/json'})
        response=conn.getresponse();return response.status,response.read().decode()
    finally:conn.close()
class Gate:
    def __init__(self,out,label,endpoint,body,delayed):
        self.out=out;self.label=label;self.endpoint=endpoint;self.body=body;self.delayed=delayed
        self.accepted=threading.Event();self.release=threading.Event();self.events=[];self.lock=threading.Lock();self.error=None
    def event(self,event,**data):
        with self.lock:self.events.append({'event':event,'monotonic_ns':time.monotonic_ns(),**data})
    def __enter__(self):
        gate=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                self.connection.settimeout(3)
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    demand(self.path=='/v3/kv/txn' and n==len(gate.body) and n<65536,'EXACT_SELECTED_REQUEST_ONLY')
                    body=self.rfile.read(n);demand(body==gate.body,'REQUEST_CHANGED')
                    gate.event('accepted',request_body=body.decode());gate.accepted.set()
                    demand(gate.release.wait(10),'RELEASE_TIMEOUT')
                    gate.event('forward',request_body=body.decode())
                    code,raw=rpc(gate.endpoint,'/v3/kv/txn',body)
                    save(gate.out/(gate.label+'_upstream_witness.json'),{'http_status':code,'raw_response':raw,'monotonic_ns':time.monotonic_ns()})
                    gate.event('upstream_complete');demand(code==200,'UPSTREAM_ERROR')
                    if not gate.delayed:
                        encoded=raw.encode();self.send_response(code);self.send_header('Content-Length',str(len(encoded)));self.end_headers();self.wfile.write(encoded)
                        gate.event('response_delivered')
                    else:gate.event('late_response_not_delivered')
                    self.close_connection=True
                except Exception as e:
                    gate.error=type(e).__name__+': '+str(e);gate.event('handler_error',error=gate.error);self.close_connection=True
        self.server=http.server.HTTPServer(('127.0.0.1',0),Handler);self.server.timeout=3
        self.thread=threading.Thread(target=self.server.handle_request,daemon=True);self.thread.start()
        if not self.delayed:self.release.set()
        return self
    @property
    def address(self):return f'http://127.0.0.1:{self.server.server_port}'
    def __exit__(self,*exc):
        self.release.set();self.thread.join(timeout=6);self.server.server_close()
        save(self.out/(self.label+'_events.json'),self.events)
        demand(not self.thread.is_alive(),'RELAY_THREAD_INCOMPLETE');demand(self.error is None,'RELAY_ERROR '+str(self.error))
def client_request(gate,out,label,body,timeout):
    result={'request_body':body.decode(),'endpoint':gate.address,'start_monotonic_ns':time.monotonic_ns()}
    try:
        code,raw=rpc(gate.address,'/v3/kv/txn',body,timeout)
        result.update(transport_result='RESPONSE_RECEIVED',http_status=code,raw_response=raw)
    except (OSError,http.client.HTTPException) as e:
        result.update(transport_result='TRANSPORT_ERROR',exception_type=type(e).__name__,exception_message=str(e))
    finally:
        result['end_monotonic_ns']=time.monotonic_ns();save(out/(label+'_client.json'),result)
    return result
def decision(out,label,receipt,read,client_state):
    data=json.loads(read['stdout']);kvs=data.get('kvs',[])
    outcome='UNKNOWN' if not kvs else ('COMMITTED' if len(kvs)==1 and base64.b64decode(kvs[0]['value']).decode()==receipt else 'ID_REUSE_MISMATCH')
    save(out/(label+'_decision.json'),{'client_state':client_state,'receipt_decision':outcome,'inputs':[label.split('_before')[0]+'_request.json',label+'_receipt_read.json'],'witness_used':False})
    return outcome
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args()
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    status={'status':'INDETERMINATE','controlling_pass':186,'classification':'NONCLAIM','promotion':False,'freeze':False,'scope':'owned transport-pending submission; no Raft-partition or production claim'}
    context={k:os.environ.get(k) for k in ['GITHUB_REPOSITORY','GITHUB_REPOSITORY_ID','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA']}
    save(out/'EXECUTION_CONTEXT.json',{'mode':'GITHUB_HOSTED' if context['GITHUB_RUN_ID'] else 'LOCAL_REHEARSAL','provider_declarations':context})
    try:
        with OwnedCluster(out,1) as c:
            c.ctl('endpoint_before',0,['endpoint','status'])
            for label,delayed,retry_pending in [('control',False,False),('late_commit',True,False),('retry_pending',True,True)]:
                prefix='/brains10/delayed/'+c.work.name+'/'+label;head=prefix+'/head';key=prefix+'/tx/T1'
                state=lambda gen:canonical({'generation':gen,'digest':f'G{gen}','authority_config':'C0','lifecycle_generation':0,'registry_digest':'R0'})
                initial=state(0);successor=state(1)
                init=json.loads(c.ctl(label+'_init',0,['txn'],build_init_script(head,key,initial))['stdout']);demand(init.get('succeeded') is True,'NAMESPACE_REUSED')
                first=json.loads(c.ctl(label+'_initial_head',0,['get',head,'--consistency=l'])['stdout']);revision=str(first['kvs'][0]['mod_revision'])
                req={'head_key':head,'transition_id':key,'expected_parent':initial,'expected_revision':revision,'successor':successor,'authority_config':'C0'}
                receipt=canonical({'request':req,'result':successor})
                txn={'compare':[{'target':'VALUE','result':'EQUAL','key':b64(head),'value':b64(initial)},{'target':'MOD','result':'EQUAL','key':b64(head),'mod_revision':revision},{'target':'VERSION','result':'EQUAL','key':b64(key),'version':'0'}],
                     'success':[{'request_put':{'key':b64(head),'value':b64(successor)}},{'request_put':{'key':b64(key),'value':b64(receipt)}}],
                     'failure':[{'request_range':{'key':b64(head),'serializable':False}}]}
                body=canonical(txn).encode();save(out/(label+'_request.json'),{'request':req,'receipt':receipt,'txn':txn,'request_body':body.decode()})
                with Gate(out,label,c.endpoints[0],body,delayed) as gate:
                    result=[];thread=threading.Thread(target=lambda:result.append(client_request(gate,out,label,body,.4 if delayed else 4)),daemon=True);thread.start()
                    demand(gate.accepted.wait(3),'REQUEST_NOT_ACCEPTED');thread.join(timeout=5);demand(not thread.is_alive() and len(result)==1,'CLIENT_INCOMPLETE')
                    client=result[0]
                    if delayed:
                        demand(client.get('exception_type')=='TimeoutError','REAL_TIMEOUT_REQUIRED')
                        read=c.ctl(label+'_before_receipt_read',0,['get',key,'--consistency=l'])
                        demand(decision(out,label+'_before',receipt,read,'UNKNOWN_COMMIT')=='UNKNOWN','ABSENCE_MUST_STAY_UNKNOWN')
                        c.ctl(label+'_before_head',0,['get',head,'--consistency=l'])
                        gate.event('absence_observed_before_release')
                        if retry_pending:
                            code,raw=rpc(c.endpoints[0],'/v3/kv/txn',body);save(out/(label+'_pending_retry.json'),{'http_status':code,'request_body':body.decode(),'raw_response':raw})
                            demand(code==200 and json.loads(raw).get('succeeded') is True,'PENDING_EXACT_RETRY_FAILED')
                            c.ctl(label+'_retry_head',0,['get',head,'--consistency=l']);c.ctl(label+'_retry_receipt',0,['get',key,'--consistency=l']);gate.event('exact_retry_committed_before_release')
                        gate.event('release');gate.release.set()
                    else:demand(client['transport_result']=='RESPONSE_RECEIVED' and json.loads(client['raw_response']).get('succeeded') is True,'CONTROL_FAILED')
                witness=json.loads((out/(label+'_upstream_witness.json')).read_text());succeeded=json.loads(witness['raw_response']).get('succeeded',False)
                demand(succeeded is (not retry_pending),'LATE_OUTCOME_UNEXPECTED')
                read=c.ctl(label+'_receipt_read',0,['get',key,'--consistency=l']);demand(decision(out,label,receipt,read,'UNKNOWN_COMMIT' if delayed else 'REPLY_RECEIVED')=='COMMITTED','RESOLUTION_FAILED')
                c.ctl(label+'_head',0,['get',head,'--consistency=l'])
                code,raw=rpc(c.endpoints[0],'/v3/kv/txn',body);save(out/(label+'_final_retry.json'),{'http_status':code,'request_body':body.decode(),'raw_response':raw});demand(code==200 and not json.loads(raw).get('succeeded',False),'DUPLICATE_WRITE')
                c.ctl(label+'_head_after',0,['get',head,'--consistency=l']);c.ctl(label+'_receipt_after',0,['get',key,'--consistency=l'])
            c.ctl('endpoint_after',0,['endpoint','status']);status['status']='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION'
    except Exception as e:status['error']=type(e).__name__+': '+str(e)
    finally:seal(out,status)
    print(json.dumps(status));return 0 if status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

"""Synthetic mapping/trace controls; no provider, signal or network calls."""
import argparse,copy,dataclasses,hashlib,json,tempfile,time,types,urllib.request
from pathlib import Path
from boundary_helpers import OwnedMember,GatewayExceptionTrace
from etcd_lifecycle_adapter import Gateway,EXCHANGE_LOG,_canonical
from owned_etcd import demand,save,sha

def select_txn(trace,body,endpoint,hook):
 digest=hashlib.sha256(body).hexdigest()
 demand(trace['post_method_unchanged'] and trace['restore_ok'] and not trace['errors'],'TRACE_VALID')
 expected=sha(Path(__file__).parent/'etcd_lifecycle_adapter.py')
 demand(trace['source_sha256_before']==trace['source_sha256_after']==expected and trace['bytecode_sha256']==hashlib.sha256(Gateway.post.__code__.co_code).hexdigest(),'TRACE_CODE')
 events=[e for e in trace['events'] if e['path']=='/v3/kv/txn']
 demand([e['event'] for e in events]==['call','exception','exception','return'],'TXN_EVENTS')
 demand(all(e['endpoint']==endpoint and e['thread_id']==trace['thread_id'] and e['code_identity_match'] and e['request_sha256']==digest for e in events),'TXN_BINDING')
 demand(events[1]['exact_timeout_type'] and events[2]['exact_connection_error_type'],'TXN_EXCEPTION_SEQUENCE')
 demand([e['event'] for e in hook]==['hook_entered','hook_completed'] and all(e['request_sha256']==digest for e in hook),'HOOK_COMPLETION')
 demand(events[0]['monotonic_ns']<hook[0]['monotonic_ns']<=hook[1]['monotonic_ns']<events[1]['monotonic_ns']<=events[2]['monotonic_ns']<=events[3]['monotonic_ns'],'HOOK_TRACE_ORDER')
 return {'call_is_submission':False,'hook_completion_is_submission':False,'matched_txn_events':len(events),'preliminary_range_events':len([e for e in trace['events'] if e['path']=='/v3/kv/range'])}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);mapping=[]
 with tempfile.TemporaryDirectory(prefix='owned-selection-model-') as td:
  c=types.SimpleNamespace(n=3,work=Path(td),endpoints=[f'http://127.0.0.1:{21000+i}' for i in range(3)],argv=[],processes={})
  for i in range(3):
   argv=['etcd','--data-dir',str(c.work/f'm{i}'),'--listen-client-urls',c.endpoints[i]];c.argv.append(argv);c.processes[i]=types.SimpleNamespace(pid=30000+i,args=argv,poll=lambda:None)
  status={'Endpoint':c.endpoints[1],'Status':{'header':{'member_id':22,'cluster_id':99}}};m=OwnedMember.select(c,1,status);m.validate(c)
  for name,value in [('index',0),('pid',999),('process',c.processes[2]),('directory',c.work/'m2'),('endpoint',c.endpoints[2]),('argv',tuple(c.argv[2])),('cluster',object())]:
   try:dataclasses.replace(m,**{name:value}).validate(c)
   except RuntimeError as e:mapping.append({'mutation':name,'rejected':True,'reason':str(e)})
   else:raise RuntimeError('MAPPING_MUTATION_ACCEPTED_'+name)
  bad=copy.deepcopy(status);bad['Endpoint']=c.endpoints[2]
  try:OwnedMember.select(c,1,bad)
  except RuntimeError as e:mapping.append({'mutation':'status_endpoint','rejected':True,'reason':str(e)})
  else:raise RuntimeError('WRONG_STATUS_ACCEPTED')
 body={'compare':[],'success':[],'failure':[]};canonical=_canonical(body);endpoint='http://127.0.0.1:1';hook=[];transport=[]
 def mark_hook(raw):
  for name in ['hook_entered','hook_completed']:hook.append({'event':name,'monotonic_ns':time.monotonic_ns(),'request_sha256':hashlib.sha256(raw).hexdigest()})
 class Response:
  def __enter__(self):return self
  def __exit__(self,*args):return None
  def read(self):return b'{}'
 def synthetic(req,**kwargs):
  transport.append({'path':req.selector,'monotonic_ns':time.monotonic_ns(),'synthetic':True})
  if req.selector=='/v3/kv/txn':raise TimeoutError('synthetic inert exception')
  return Response()
 original=urllib.request.urlopen;g=Gateway(endpoint);g.before_txn=mark_hook;tracer=GatewayExceptionTrace();caught=False
 try:
  urllib.request.urlopen=synthetic
  with tracer:
   g.post('/v3/kv/range',{'key':'aW5lcnQ=','serializable':False})
   try:g.post('/v3/kv/txn',body)
   except ConnectionError:caught=True
 finally:urllib.request.urlopen=original
 demand(caught and urllib.request.urlopen is original,'SYNTHETIC_RESTORE');trace=tracer.record();positive=select_txn(trace,canonical,endpoint,hook);negatives=[]
 for name in ['wrong_body','wrong_thread','wrong_code','wrong_endpoint','missing_hook_completion','hook_after_exception']:
  t=copy.deepcopy(trace);h=copy.deepcopy(hook);b=canonical;ep=endpoint
  if name=='wrong_body':b=b'wrong'
  elif name=='wrong_thread':next(e for e in t['events'] if e['path']=='/v3/kv/txn')['thread_id']+=1
  elif name=='wrong_code':t['bytecode_sha256']='0'*64
  elif name=='wrong_endpoint':ep='http://127.0.0.1:2'
  elif name=='missing_hook_completion':h.pop()
  elif name=='hook_after_exception':h[1]['monotonic_ns']=t['events'][-1]['monotonic_ns']+1
  try:select_txn(t,b,ep,h)
  except RuntimeError as e:negatives.append({'mutation':name,'rejected':True,'reason':str(e)})
  else:raise RuntimeError('TRACE_MUTATION_ACCEPTED_'+name)
 result={'status':'PASS_INERT_CONTROLS','scope':'SYNTHETIC_MAPPING_AND_TRANSACTION_TRACE_ONLY','mapping_negatives':mapping,'trace_positive':positive,'trace_negatives':negatives,'trace':trace,'hook':hook,'synthetic_transport':transport,'network_calls':0,'provider_started':False,'actual_kernel_timeout':False,'actual_selected_member_pause':'NOT_TESTED_HERE','controlling_pass':186,'classification':'NONCLAIM'};save(out/'RESULT.json',result);print(json.dumps({'status':result['status'],'mapping_negatives':len(mapping),'trace_negatives':len(negatives)}));return 0
if __name__=='__main__':raise SystemExit(main())

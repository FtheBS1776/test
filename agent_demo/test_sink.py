"""Local process/crash/duplicate/mismatch tests; no provider required."""
import argparse,concurrent.futures,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from report_sink import deliver,observe,initialize
from owned_etcd import demand,save
import stateful_subject as st
ROOT=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args();results=[]
 e={'effect_id':st.EID('task','publish','genie-report-inbox'),'transition_id':'task','kind':'publish','target':'genie-report-inbox','payload':'report','generation':1,'authority_config':'C1'}
 with tempfile.TemporaryDirectory(prefix='genie-sink-test-') as td:
  p=Path(td);db=p/'inbox.sqlite'
  demand(observe(db,e)=='UNKNOWN','FAKE_STDOUT_CANNOT_CONFIRM_ABSENT_SINK');results.append('absent_sink_remains_unknown')
  def process(path,effect=e,crash='none'):
   return subprocess.run([sys.executable,'-B',str(ROOT/'report_sink.py'),str(path),'--crash',crash],input=json.dumps(effect),capture_output=True,text=True,timeout=15)
  r=process(db);demand(r.returncode==2 and not db.exists(),'NO_IMPLICIT_PROVISIONING');results.append('unprovisioned_sink_rejected');initialize(db)
  r=process(db,crash='before_commit');demand(r.returncode==72 and r.stdout=='' and observe(db,e)=='UNKNOWN','PRECOMMIT_CRASH');results.append('precommit_exit_no_application')
  r=process(db,crash='after_commit');demand(r.returncode==73 and r.stdout=='' and observe(db,e)=='CONFIRMED','POSTCOMMIT_CRASH');results.append('postcommit_exit_retains_one_application_without_reply')
  r=process(db);demand(r.returncode==0 and json.loads(r.stdout)=={'delivery':'DUPLICATE'} and observe(db,e)=='CONFIRMED','RETRY');results.append('same_request_retry_deduplicated')
  for label,bad in [('payload',{**e,'payload':'other'}),('target',{**e,'target':'elsewhere'}),('bool_generation',{**e,'generation':True}),('effect_id',{**e,'effect_id':'unbound'})]:
   r=process(db,bad);demand(r.returncode==2 and observe(db,e)=='CONFIRMED','BAD_'+label);results.append('reject_'+label)
  concurrent_db=p/'concurrent.sqlite';initialize(concurrent_db)
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rs=list(pool.map(lambda _:process(concurrent_db),range(4)))
  save(Path(a.output),{'status':'CHECKING_CONCURRENCY','processes':[{'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr} for r in rs]});demand(all(r.returncode==0 for r in rs),'CONCURRENT_PROCESS_FAILURE');outcomes=[json.loads(r.stdout)['delivery'] for r in rs];demand(outcomes.count('APPLIED')==1 and outcomes.count('DUPLICATE')==3 and observe(concurrent_db,e)=='CONFIRMED','CONCURRENT_DUPLICATE');results.append('four_concurrent_deliveries_one_application')
 save(Path(a.output),{'status':'PASS','tests':results,'count':len(results),'scope':'LOCAL_OWNED_SQLITE_SINK','physical_power_loss':False});print(json.dumps({'status':'PASS','tests':len(results)}))
if __name__=='__main__':main()

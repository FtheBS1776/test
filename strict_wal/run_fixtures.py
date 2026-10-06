"""Strict decoder tests on exact retained bytes; no provider execution."""
import argparse,base64,copy,hashlib,json,subprocess
from pathlib import Path
from owned_etcd import demand,save,sha
from verify_control import normalized
ROOT=Path(__file__).resolve().parent
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--observer',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(a.observer).resolve();recipe=json.loads((ROOT/'FIXTURE_RECIPE.json').read_text());prefix=base64.b64decode(recipe['prefix_b64'],validate=True)
 demand(len(prefix)==recipe['prefix_bytes'] and recipe['prefix_bytes']+recipe['zero_suffix_bytes']==recipe['original_file_bytes'],'RECIPE_COUNTS')
 expected=recipe['expected_observer'];txn=json.loads(base64.b64decode(recipe['expected_adapter_request_b64'],validate=True));normalized(txn)
 def case(name,data,size=None):
  dest=out/name;(dest/'snapshot/member/wal').mkdir(parents=True);(dest/'snapshot/member/snap').mkdir();f=dest/'snapshot/member/wal/0000000000000000-0000000000000000.wal'
  with f.open('wb') as stream:
   stream.write(data)
   if size is not None:stream.truncate(size)
  digest=sha(f);save(dest/'INPUT_MANIFEST.json',{str(f.relative_to(dest/'snapshot')):digest})
  if name=='exact_prior_input':demand(digest==recipe['original_wal_sha256'],'EXACT_RECONSTRUCTION_MISMATCH')
  p=subprocess.run([str(exe),str(dest/'snapshot')],capture_output=True,timeout=15);(dest/'OBSERVER.stdout').write_bytes(p.stdout);(dest/'OBSERVER.stderr').write_bytes(p.stderr);save(dest/'COMMAND.json',{'argv':[str(exe),str(dest/'snapshot')],'returncode':p.returncode,'observer_sha256':sha(exe),'timeout_seconds':15});demand(sha(f)==digest,'INPUT_MUTATED')
  return dest,p,digest
 result={'classification':'RECONSTRUCTED_PRIOR_AND_SYNTHETIC_FIXTURE_NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False,'provider_executed':False,'live_capture':False,'cases':[]}
 dest,p,digest=case('exact_prior_input',prefix,recipe['original_file_bytes']);demand(p.returncode==0,'POSITIVE_DECODE_REJECTED');decoded=json.loads(p.stdout);terminal=decoded.pop('terminal');demand(decoded['schema']=='WAL_DECODE_V2' and decoded['scope']=='INITIAL_SEGMENT_READ_ONLY_DECODE','V2_SCOPE');decoded['schema']=expected['schema'];decoded['scope']=expected['scope'];demand(decoded==expected,'COMPLETE_PRIOR_DECODE_CHANGED')
 demand(terminal['condition']=='EOF' and terminal['file_sha256']==digest and terminal['last_valid_offset']==len(prefix) and terminal['zero_suffix_bytes']==recipe['zero_suffix_bytes'] and terminal['file_size']==recipe['original_file_bytes'] and terminal['canonical_frames_and_padding'] is True and terminal['unexpected_eof_accepted'] is False,'TERMINAL_BINDING')
 target=[e for e in decoded['entries'] if e['request'] and e['request'].get('txn') and len(e['request']['txn']['success'])==4];demand(len(target)==1 and normalized(target[0]['request']['txn'],True)==normalized(txn),'FULL_HTTP_TXN_BINDING');result['cases'].append({'name':'exact_prior_input','status':'PASS','sha256':digest,'terminal':terminal,'full_prior_decode':'IDENTICAL_AFTER_EXPLICIT_SCHEMA_SCOPE_COMPARISON','exact_adapter_txn':'MATCH','entry_index':target[0]['index']})
 padding=bytearray(prefix);demand(padding[12:16]==b'\0'*4,'EXPECTED_FIRST_FRAME_PADDING');padding[12]=1
 negatives=[('partial_declared_frame',prefix+(128).to_bytes(8,'little')+b'\x08\x03\x10\x00','strict_terminal_error'),('nonzero_after_zero_header',prefix+b'\0'*8+b'nonzero-tail','nonzero_tail_after_terminal_eof'),('nonzero_frame_padding',bytes(padding),'nonzero_padding')]
 for name,data,reason in negatives:
  dest,p,digest=case(name,data);demand(p.returncode!=0 and reason in p.stderr.decode(),'NEGATIVE_NOT_REJECTED_'+name);result['cases'].append({'name':name,'status':'EXPECTED_FORMAT_REJECTION','returncode':p.returncode,'sha256':digest,'reason':reason})
 dest,p,digest=case('valid_prefix_without_target',prefix[:recipe['valid_prefix_cut']]);demand(p.returncode==0,'VALID_PREFIX_FORMAT_REJECTED');v=json.loads(p.stdout);demand(v['terminal']['condition']=='EOF' and v['terminal']['file_sha256']==digest and v['commit_index']==6 and [e['index'] for e in v['entries']]==[1,2,3,4,5,6],'VALID_PREFIX_READ_BINDING');demand(not any(e['request'] and e['request'].get('txn') and len(e['request']['txn']['success'])==4 for e in v['entries']),'TARGET_UNEXPECTEDLY_PRESENT');result['cases'].append({'name':'valid_prefix_without_target','status':'FORMAT_VALID_TARGET_PREDICATE_REJECTED','returncode':p.returncode,'sha256':digest,'reason':'TARGET_ENTRY_MISSING','commit_index':v['commit_index']})
 result['status']='PASS_BOUNDED_OBSERVER_FIXTURES';save(out/'RESULT.json',result);save(out/'FIXTURE_MANIFEST.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='FIXTURE_MANIFEST.json'});print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())

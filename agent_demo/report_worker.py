"""Deterministic report transformation; no runtime LLM inference."""
import argparse,hashlib,json
from pathlib import Path

def render(raw):
 d=json.loads(raw)
 if d.get('status')!='PASS' or d.get('classification')!='NONCLAIM':raise ValueError('VERIFIED_SCOPE_REQUIRED')
 fields=['target_entry','saved_wal_commit','pretrial_applied','final_applied','copy_to_timeout_margin_ns','adapter_txns','atomic_revision']
 if any(type(d.get(k)) is not int or d[k]<0 for k in fields):raise ValueError('EXACT_MEASUREMENT_TYPES')
 if d.get('uncommittedness_proven') is not False or d.get('durability_proven') is not False or d.get('production_trust_proven') is not False:raise ValueError('SCOPE_EXPANSION')
 negatives=d['model_negatives']
 if len(negatives)!=20 or any(x.get('rejected') is not True for x in negatives):raise ValueError('INCOMPLETE_NEGATIVES')
 return ('# Genie interruption-and-resume task report\n\n'
 'This report was generated from the verified pending-transaction experiment.\n\n'
 f"- Exact transaction entry: {d['target_entry']}.\n"
 f"- Log copy completed {d['copy_to_timeout_margin_ns']/1e9:.9f} seconds before the original client timeout.\n"
 f"- Same-request recovery used {d['adapter_txns']} transaction submissions and one committed state transition.\n"
 f"- Final records shared revision {d['atomic_revision']}; all {len(negatives)} altered models were rejected.\n\n"
 'The experiment supports safe handling of uncertainty in its bounded fixture. It does not establish production trust or physical durability.\n\n'
 f"Input SHA-256: `{hashlib.sha256(raw).hexdigest()}`\n").strip().encode()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');a=ap.parse_args();result=render(Path(a.input).read_bytes())
 with Path(a.output).open('xb') as f:f.write(result)
 print(json.dumps({'worker':'deterministic-report-transform','result_sha256':hashlib.sha256(result).hexdigest(),'runtime_llm_inference':False}))
if __name__=='__main__':main()

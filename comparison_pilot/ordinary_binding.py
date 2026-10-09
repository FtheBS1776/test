"""Ordinary root-owned artifact metadata checks, not a new authority mechanism."""
import hashlib,json
from pathlib import Path

def verify(plan,metadata,path,attempt):
 if type(metadata) is not dict:raise ValueError('METADATA')
 if any(metadata.get(k)!=plan[k] for k in ('task_id','input_sha256')):raise ValueError('TASK_INPUT_BINDING')
 if type(metadata.get('attempt')) is not int or metadata['attempt']!=attempt:raise ValueError('ATTEMPT_BINDING')
 raw=Path(path).read_bytes()
 if metadata.get('sha256')!=hashlib.sha256(raw).hexdigest() or type(metadata.get('bytes')) is not int or metadata['bytes']!=len(raw):raise ValueError('CONTENT_BINDING')
 if not 0<len(raw)<=12000:raise ValueError('CANDIDATE_BOUND')
 return raw

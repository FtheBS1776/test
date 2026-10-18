import hashlib,json,pathlib,stat,zipfile
base=pathlib.Path('/workspace/scratch/27265db857a2')
p=base/'GENIE_OPERATOR_GUIDANCE_REVIEW_INPUT_v6_20261018.zip'
expected='e2fd22c1b50698de5afc4539e3604ff8207aca3b2012182ef30ee239625c10f5'
actual=hashlib.sha256(p.read_bytes()).hexdigest(); assert actual==expected
prefix='GENIE_OPERATOR_GUIDANCE_REVIEW_INPUT_v6_20261018/'
with zipfile.ZipFile(p) as z:
 names=z.namelist();assert len(names)==len(set(names))
 for info in z.infolist():
  q=pathlib.PurePosixPath(info.filename)
  assert str(q)==info.filename and not q.is_absolute() and '..' not in q.parts and '\\' not in info.filename
  assert info.filename.startswith(prefix) and not info.is_dir()
  assert not stat.S_ISLNK(info.external_attr>>16)
 assert z.testzip() is None
 manifest_bytes=z.read(prefix+'MANIFEST.json');manifest=json.loads(manifest_bytes)
 fs=manifest['files']; paths=[f['path'] for f in fs];assert len(paths)==len(set(paths))
 assert set(names)=={prefix+'MANIFEST.json'}|{prefix+v for v in paths}
 for f in fs:
  data=z.read(prefix+f['path']);assert len(data)==f['size'];assert hashlib.sha256(data).hexdigest()==f['sha256']
  extracted=base/'operator_guidance_review_v6/input'/prefix/f['path'];assert extracted.read_bytes()==data
 print(json.dumps({'status':'PASS','outer_sha256':actual,'zip_entry_count':len(names),'manifest_payload_count':len(fs),'manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),'all_paths_canonical_unique':True,'no_symlinks':True,'crc_all_pass':True,'manifest_lengths_hashes_exact_set':True,'extracted_bytes_identical':True,'source_commit_identity_only':manifest['source_commit'],'source_tree_identity_only':manifest['source_tree'],'subject_identities':[f for f in fs if f['path'] in ['source/README.md','source/active_runner/README_FIRST.md','source/run_queue/README_FIRST.md','source/worker_substitution/QUICKSTART.md','source/session_driver/USAGE.md','source/desktop_plugin/README_FIRST.md']]},indent=2))

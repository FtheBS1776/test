"""Preserved follow-up; cannot retroactively fix the first extraction order."""
import hashlib,json,pathlib,runpy,zipfile
here=pathlib.Path(__file__).resolve().parent
# Verification reads every member directly from ZIP and checks initial extracted bytes.
runpy.run_path(str(here/'verify_input.py'),run_name='__verification__')
second=here/'verified_second_extraction'
assert not second.exists()
second.mkdir()
archive=here.parent/'GENIE_OPERATOR_GUIDANCE_REVIEW_INPUT_v6_20261018.zip'
with zipfile.ZipFile(archive) as z:
 z.extractall(second)
 original=here/'input'
 for name in z.namelist():
  assert (original/name).read_bytes()==(second/name).read_bytes()==z.read(name),name
 assert {str(p.relative_to(second)) for p in second.rglob('*') if p.is_file()}==set(z.namelist())
 print(json.dumps({'status':'PASS','ordered_followup':'full archive manifest verification completed before creating second exclusive extraction','second_extracted_files':len(z.namelist()),'initial_second_archive_all_bytes_identical':True,'initial_ordering_limitation_remains':True},sort_keys=True))

# Initial attempts and ordering limitation (transcribed from tool results)

These are the original steps, retained explicitly; this file is a transcription, not a fresh raw capture or a claim that the ordering was compliant. Nothing from the first extraction was removed or relabeled. The complete initial extraction remains in `input/`.

1. The first shell call was `pwd && ls -l GENIE_OPERATOR_GUIDANCE_REVIEW_INPUT_v6_20261018.zip && test ! -e operator_guidance_review_v6 && mkdir operator_guidance_review_v6`. Exit 0. It reported cwd `/workspace/scratch/27265db857a2` and archive length 178202 bytes.
2. The original extraction program below ran next. Exit 0. It printed outer SHA256 `e2fd22c1b50698de5afc4539e3604ff8207aca3b2012182ef30ee239625c10f5` and the archive member names. It checked outer SHA, uniqueness, traversal/absolute/backslash paths, symlinks and CRC, then extracted. It did not yet check all manifest lengths/hashes/exact set.
3. Next, `cat` read the supplied `README_FIRST.md`, `REVIEW_CONTRACT.md` and `MANIFEST.json`; exit 0. The README's verification-before-extraction requirement had therefore not been followed for the first extraction.
4. `verify_input.py` was created and run once, capturing `integrity.raw.json`. It verified the full archive manifest and initial extracted byte equality before any subject documentation/source review or execution.
5. The only executed subject functions were those used by `fresh_guidance_checks.py`. That script was created once and executed once with `python -B`; its complete stdout/stderr and all fresh stores are preserved. No failing or abandoned probe source was replaced, and no historical fixture or subject main was run.
6. On parent follow-up, `verify_then_extract_again.py` ran once. `ordered_followup.raw.txt` records full direct-from-ZIP manifest verification before creation of `verified_second_extraction/`, followed by exact equality with the original inspected bytes and archive. This is an identity check in the requested order, not retroactive compliance for step 2. The fake-only checks were not rerun.

## Original initial extraction program (preserved; not rerun)

```python
import hashlib,zipfile,pathlib,stat,json
p=pathlib.Path('GENIE_OPERATOR_GUIDANCE_REVIEW_INPUT_v6_20261018.zip')
expected='e2fd22c1b50698de5afc4539e3604ff8207aca3b2012182ef30ee239625c10f5'
h=hashlib.sha256(p.read_bytes()).hexdigest(); assert h==expected,(h,expected)
z=zipfile.ZipFile(p); names=z.namelist(); assert len(names)==len(set(names))
for i in z.infolist():
 q=pathlib.PurePosixPath(i.filename)
 assert not q.is_absolute() and '..' not in q.parts and '\\' not in i.filename,i.filename
 assert not stat.S_ISLNK(i.external_attr>>16),i.filename
assert z.testzip() is None
out=pathlib.Path('operator_guidance_review_v6/input');out.mkdir()
z.extractall(out)
print(json.dumps({'outer_sha256':h,'archive_entries':names},indent=2))
```

The initial archive-names output is available in the original tool transcript. The preserved input manifest and both extractions carry the identical member set; this transcription does not masquerade as saved raw stdout from that first attempt.

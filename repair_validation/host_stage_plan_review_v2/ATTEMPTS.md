# Attempts

1. Read-only `ls -l` of supplied ZIP: succeeded; 157580 bytes.
2. Read-only standard-library Python outer digest and ZIP central-directory inventory: digest matched, 56 entries, no extraction.
3. Read-only standard-library Python directly read MANIFEST.json, README_FIRST.md and REVIEW_CONTRACT.md from ZIP: succeeded. No subject code imported or executed.
4. `verification.py` below performs complete pre-extraction verification and exclusive extraction; source and raw output retained. No earlier extraction, failed attempt, source edit or subject execution.

Initial three reconnaissance calls are preserved here as an action record; their read data are fully retained in the immutable input and the per-entry verification output.

5. Read-only `nl`, `sed` and `rg` over verified plan, builder/spec/locks, helper/entry/binder, import-chain modules and JSON/workflow configs. Supporting reads retained in `inspected_source.numbered.txt`; no subject execution.
6. Created and ran reviewer-owned `static_checks.py`: AST/literal lock comparison, top-level structure inventory and JSON identity inspection. Exit 0, stdout/stderr retained. No subject imports.
7. Created REVIEW.md, numbered source capture, final artifact/source integrity check and exclusive review ZIP. No retry, reset, removal or subject modification.

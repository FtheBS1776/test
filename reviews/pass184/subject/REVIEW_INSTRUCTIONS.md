# Review instructions

Start only after `VERIFY_GATE.py` reports `VERIFY_GATE_PASS`.

Independently inspect the subject and run:

```sh
python3 -m unittest discover -v
```

Do not trust successful tests as the verdict. Record actual commands and
results. Attempt practical adversarial or mutation checks when justified.

Return one ZIP containing exactly these six top-level files:

1. `README_FIRST.md` — return-package instructions.
2. `REVIEWER_REPORT.md` — scope, independent attack model, evidence, findings,
   residual HOLDs, and disposition.
3. `REVIEW_RETURN.json` — machine-readable disposition (`NO_DEFECT_FOUND`,
   `DEFECT_FOUND`, `GATE_INVALID`, or `HOLD`) and file bindings.
4. `REVIEW_SUBJECT_SHA256.txt` — the manifest hash and each reviewed subject
   file hash.
5. `RETURN_SHA256SUMS.txt` — SHA-256 for the other five return files.
6. `RETURN_VERIFY.py` — verifies the return structure and hashes.

The report must distinguish a demonstrated defect from a limitation that is
already explicitly outside the reference-model scope. Do not repair the
subject. Do not claim a production, independent-authority, or R2 result.

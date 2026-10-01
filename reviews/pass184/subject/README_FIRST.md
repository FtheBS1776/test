# Pass 184 strict-blind review gate — instruction revision 2

Read this file first. Treat this directory as the complete review input.

This is a bounded nonclaim reference-model review of the listed policy
selection, transition, and receipt-composition modules. It is not a production
backend, a provider exercise, or R2/EXP010 work.

Do not use prior conversation, controller status, package history, defect
labels, external review conclusions, or source files outside this directory.
Do not repair, modify, promote, integrate, execute provider actions, retrieve
live provider evidence, or perform theory-bearing interpretation. The sole
external-research exception is public technical literature, after deriving
your initial attack model, as specified in REVIEW_SCOPE.md. Do not retrieve
project history, earlier reviews, credentials, live revocation objects, or
beacon data. Firecrawl remains prohibited.

1. Compute this gate ZIP's outer SHA-256 when supplied by the controller and
   compare it against the separately supplied expected value.
2. Test ZIP integrity and extract cleanly.
3. Run `python3 VERIFY_GATE.py` from this directory.
4. Read `REVIEW_INSTRUCTIONS.md` and `REVIEW_SCOPE.md`.
5. Derive an independent adversarial model, inspect only the listed source and
   test files, and run the included test suite.
6. Produce exactly the six-file return described in `REVIEW_INSTRUCTIONS.md`.

If gate verification fails, return a six-file review package whose disposition
is `GATE_INVALID`; do not continue to subject review.

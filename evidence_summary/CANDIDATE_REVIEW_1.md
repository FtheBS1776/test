# Candidate source review — NONCLAIM

Disposition: NO_DEFECT_FOUND within this static review of the fixed contract. Root acceptance tests and adjudication remain required; this is not proof of absence of defects.

## Exact subject and binding

Reviewed only `evidence_summary/output/report_logs_1.py` against `evidence_summary/CONTRACT.md`, with the correspondence, primary-source research note, plan and supplied status as context. Independently computed candidate SHA256 `593804224f0c3e8ea5a8206825a6e000bca7d41b159301b09e9db0c1f066518d` and size5942 bytes; both match the expected subject and STATUS_1.json. The status task ID `genie-evidence-summary-20261009`, input SHA256 `dda42c4f55346ed1d4e46df230c02eb22c98f19c6e99f35dceb23e4bab83599a` and attempt1 match PLAN.json. This is a consistency check, not authentication of the author/status issuer.

Read unchanged `comparison_pilot/validation_summary.py` to inspect reuse. Its independently computed SHA256 is `5e635b97b764c0f88ae8e497ca48ec76e480d677610b24915cc2e900e681d826`, matching the fixed pin. No acceptance suite/results were read. No candidate or dependency execution, compilation or tests were performed; source was not changed.

## Adversarial analysis

Invalid specifications are checked completely before `_load_summarize` or any input open: exact list/dict/string types, cardinality, keys, path length/NUL, supported format and duplicate exact paths. A late invalid element therefore cannot cause an earlier input read. Path aliases/inodes are deliberately outside the uniqueness contract.

Each captured input is opened binary, checked through descriptor `fstat` for regular-file status, and read once with LIMIT+1. The nonblocking opener avoids the ordinary FIFO-writer wait on platforms exposing O_NONBLOCK; it does not create a general deadline or hostile-path guarantee. Oversized snapshots reject without publishing partial-prefix hashes/counts. Ordinary open/read/fstat/close OSError or ValueError becomes an UNREADABLE entry. Captured bytes are hashed before strict UTF8 decoding; invalid encoding retains that exact captured hash/size and a REJECT summary. Valid text is passed directly to the reused parser, without reopening the pathname or executing its contents. File mutation during reading remains a possible mixed captured snapshot, which the contract explicitly does not represent as atomic file currentness.

Dependency verification uses a fixed repository-relative lookup, bounded binary read and SHA256 comparison. Compilation/import then uses the verified `raw` bytes, avoiding an import loader's second pathname read or cached bytecode. Changing the dependency after capture cannot substitute later source bytes into that invocation. The bounded read is sufficient for the pinned small source: extra bytes within the read alter the digest; an oversized prefix cannot equal the exact smaller pinned content merely by placing that content at the beginning. Trust in the fixed local source and repository layout remains explicit; this is not path confinement or authenticated provenance.

The wrapper preserves parser summaries, including FAIL, NO_COVERAGE and REJECT. It supplies no aggregate PASS/count and sets execution/fresh-sink claims to NONE. A malformed log remains CAPTURED with its raw-byte binding and parser rejection; a read/size/encoding rejection does not manufacture positive coverage. Report entry order and supplied path/format are retained.

CLI assembly and JSON serialization precede exclusive output creation. `x` mode preserves existing files/directories/symlinks and does not create missing parents. Write or context-close OSError becomes the explicit REJECT response; a newly-created incomplete output is retained because there is no cleanup, overwrite or retry. Success means report writing, regardless of individual log results. Duplicate output options reject through the custom action; unsupported arguments/formats and invalid input lists reject before output creation. No publication atomicity, crash durability or rollback resistance follows from this behavior.

## Proportional root follow-up checks

Use the frozen suite to confirm: an invalid final specification performs no input opens; exact boundary/one-byte-over files; nonregular input handling without a FIFO writer on the actual platform; strict invalid UTF8 versus malformed valid text; unchanged parser results for FAIL/NO_COVERAGE; hash binding when the input pathname changes after capture; dependency substitution between verification and import; existing/dangling symlink preservation; and injected write/close errors preserving newly-created partial output with REJECT. Such checks strengthen only the specified trusted-host behavior, not hostile filesystem isolation or a general IO deadline.

Same configured model, host and ancestry as other roles. This source review is not independent evidence, does not approve future repaired bytes, and does not replace root tests or exact accepted-code sink readback. No promotion, freeze, spending, installation, framework, provider, deployment or old experiment was performed. Existing scoped HOLDs remain unchanged.

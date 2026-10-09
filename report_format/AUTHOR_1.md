# Author attempt 1

Task: genie-direct-check-logs-20261009
Input SHA-256: de5ad087ce501c6d4277999e9cb4b30a2758e4182895fbccb30b603ca86d7286
Attempt: 1
Candidate: evidence_summary/output/report_logs_checks_1.py
Candidate SHA-256: ca49d3b8b83ecccaa4c4a252686fb755c6196fa673e0ed3249a34d4b3ff1344e
Candidate UTF-8 bytes: 8614
Baseline SHA-256: 593804224f0c3e8ea5a8206825a6e000bca7d41b159301b09e9db0c1f066518d

Added explicit checks format without changing legacy unittest/json dispatch or the pinned parser bytes. Complete rich JSON decoding rejects duplicate keys, nonstandard constants and floating overflow, including ignored metadata. Complete decoded JSON also must encode as strict UTF-8. Structural projection retains only status/count/check/flag, exposes sorted ignored field names, and delegates summary rules to the unchanged pinned parser. Original capture hashes and sizes stay tied to original input bytes. Projection stays null for capture/encoding/JSON/structural failures; it remains recorded when a structurally valid core is rejected by the parser.

Own checks: read the contract, prior correspondence/attack, frozen test source, baseline and saved dispatch; checked exact task/input/integer attempt binding; used asserted textual replacements against baseline; computed candidate hash and byte count. Candidate was not executed, imported or compiled; author ran no tests. Root validation is distinct.

Caveats: projection does not verify metadata or establish execution/currentness/authenticity. Ignored names are reported, not their values. Trusted serial local-file scope, ordinary exclusive output creation, no immutable multi-file snapshot or hostile-path confinement. Existing maintained source, strict parser, contracts, tests and stores were not changed by author.

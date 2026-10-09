# Explicit checks-format reporter review — NONCLAIM

Recommendation: ACCEPT the exact candidate within the fixed maintenance contract, subject to root's planned legacy/supplementary regressions and original-log application. No concrete repair defect found in this static review.

Independently computed `evidence_summary/output/report_logs_checks_1.py` SHA256 `ca49d3b8b83ecccaa4c4a252686fb755c6196fa673e0ed3249a34d4b3ff1344e`, size8614 bytes, matching the nominated source. Read CONTRACT.md, PRIOR_CORRESPONDENCE_AND_ATTACK.md, frozen test_checks_format.py, baseline reporter and exact candidate. Did not execute/import/compile/test code, inspect result files, alter sources, mutate databases, spawn agents or use network. Root's reported23 checks are not independently reproduced here.

## Projection and binding

The new checks format is explicit in spec validation. The original capture path remains unchanged: bounded binary capture, regular-file descriptor check, strict UTF8 decoding, SHA256 and byte count derived from captured raw bytes. Projection is computed from that captured string and never substitutes a core/projection hash for original evidence. No additional input read or standalone projection file is introduced. Read/oversize/invalid UTF8 failures leave checks projection null; valid decoded but malformed JSON remains CAPTURED with raw binding and rejected summary.

JSON decoding rejects nested duplicate keys and nonstandard constants; the parse_float hook rejects overflow-to-infinity even in ignored metadata. Full decoded-data serialization with strict UTF8 encoding also rejects lone surrogate content in metadata/keys rather than silently discarding it. This is confined to checks mode and does not change legacy parsing. Deep JSON/serialization recursion and ordinary malformed/value/type/overflow errors return REJECT with null projection.

Structural extraction requires top status/count/checks, checks list, each check object with a check field and exactly one passed/rejected field. Noncore values supply no decision inputs. The compact core contains only the stated three top fields and each check's name/flag. The unchanged pinned parser retains exclusive responsibility for status/count/flag/name types, count consistency, declared-vs-actual result, FAIL and zero coverage. Both flag fields or a missing flag is invalid projection; an extracted but inconsistent core keeps the disclosure and receives parser REJECT. A per-check status REJECT alongside passed true is intentionally metadata, not a contradiction within the declared core contract. Do not describe this as verification of that ignored status.

Disclosure contains exactly the declared scope plus sorted noncore top names and sorted distinct noncore check names. No metadata values are copied. Empty extras produce empty arrays. Counts/names/status are not inferred from metadata or per-check status. Disclosure is representation accounting, not validation of the ignored assertions.

## Legacy and resource limits

Direct source comparison shows the legacy unittest/json paths still call the same pinned summarize implementation on the original captured text. Legacy entry schemas receive no projection field. Loader source bytes/pin, spec cardinality/exact duplicates, read failure handling, report claims, CLI exclusive creation/preservation and partial-write behavior are retained. json mode continues to reject rich extra-field schemas; accepting checks mode does not relax it.

Raw input remains capped1 MiB per file and1..8 files. JSON decoding, full metadata reserialization/encoding, core creation/serialization and sorted disclosure add allocations and CPU work. These are not a constant-memory or deadline guarantee; ordinary buffered read-ahead is also inherited, not newly eliminated. No speedup, memory reduction, atomic multi-file snapshot, file-currentness/authenticity or metadata verification follows from this maintenance. Output names can be substantial within admitted inputs; there is no separate output-byte quota in the contract.

## Useful targeted follow-ups

The frozen23 cases cover positive/negative flags, zero coverage, core inconsistency, structurally invalid projection, nested duplicate/nonfinite metadata, ignored-name sorting, legacy separation and actual CLI preservation. Suitable supplementary probes include escaped lone surrogates in ignored metadata/key versus a valid surrogate pair; deep ignored metadata returning REJECT rather than escaping build_report; invalid UTF8 and exact/one-byte-over capture in checks mode retaining null projection; structurally extracted invalid check names/status retaining disclosure; and mixed input formats preserving order and their distinct entry schemas. These are focused extension checks, not new generic prerequisites.

Root's planned30 legacy and7 supplementary checks should explicitly target these candidate bytes rather than accidentally loading the baseline. Applying checks directly to the saved29/12 original logs and comparing prior projections is application correspondence, not a fresh run of those historical tests. Preserve original log/report/projection bytes and report their raw hashes; no new execution claim follows from matching summaries.

Same configured model/host/ancestry, not independent evidence or strict-blind review. Static recommendation applies only to the exact hashed candidate; root controls execution, adjudication and exact accepted-code fresh destination readback. Existing assurance HOLDs and historical subject identities remain; no authority promotion, freeze, spending, deployment, provider/framework or old experiment was performed.

# GitHub evidence run history — NONCLAIM

## Run 37193445374, attempt 1

- Branch: `nonclaim/pass219-etcd-integration-20261004`
- Subject commit: `88960c9d024bcfba1dd9ae414b81a04fff5b3e25`
- Event: `push`; workflow: `.github/workflows/pass219-etcd-integration.yml`
- Artifact: `pass219-etcd-integration-evidence-37193445374-1`, ID `11300151604`
- GitHub-reported artifact SHA-256: `8301cbdcea1395bafabed2cd2c0f2cb34e5cd9dc31978b6ff646b9ae9a31115c`
- Independently downloaded archive: CRC valid; all 37 evidence members matched `EVIDENCE_MANIFEST.json`; outer SHA-256 matched the GitHub digest.
- Result: `INDETERMINATE`; integration suite 8/14. No conformance claim.

The observed issues were (1) empty etcd Range results omitted default-valued `count` and `kvs` fields, which the candidate incorrectly treated as malformed, and (2) the lifecycle-mutation test fixture called `_read_raw` on `Gateway` instead of the adapter. The candidate was corrected to accept omitted protobuf default fields only when both are absent, and the fixture now reads through the adapter. The failed artifact is retained as counterevidence; a rerun must independently verify the new subject commit and artifact before adjudication.

GitHub run: https://github.com/FtheBS1776/test/actions/runs/37193445374

## Run 37193595951, attempt 1

- Branch: `nonclaim/pass219-etcd-integration-20261004`
- Subject commit: `8f80b8b42d8d297ebe9a127187b23bd4fa3a077d`
- Event: `push`; workflow: `.github/workflows/pass219-etcd-integration.yml`
- Artifact: `pass219-etcd-integration-evidence-37193595951-1`, ID `11299324231`
- GitHub-reported artifact SHA-256: `710ce0e040ea4d7c6f3c0d70cdf8f6b06d9d66fa97d5287deee8d25a2145968f`
- Independently downloaded archive: CRC valid; all 38 evidence members matched `EVIDENCE_MANIFEST.json`; outer SHA-256 matched the GitHub digest.
- Result: `INDETERMINATE`; integration suite 9/13. No conformance claim.

The remaining failures all followed a valid Compare/Txn response where etcd omitted the protobuf default `succeeded:false`. The adapter treated the absent field as malformed/uncertain. It now interprets that field omission as a definite compare failure, contingent on the response header and surrounding response being valid, then performs exact stable-ID reconciliation. This failed artifact is retained as counterevidence.

GitHub run: https://github.com/FtheBS1776/test/actions/runs/37193595951

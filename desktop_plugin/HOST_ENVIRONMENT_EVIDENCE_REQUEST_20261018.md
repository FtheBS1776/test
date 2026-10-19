# Complete host startup-source review request — current next action

The reported one-run synthetic test passed its exact success predicate on PowerShell 7.6.5 / .NET 10.0.11, exit 0 with empty stderr. This supports the provider-removal correction but does not validate the full startup/check scripts or the historical cause. The original pinned contracts/tests, failed attempts and diagnostic evidence remain unchanged. Prior versions of this request are retained in Git history; the completed four-file/excerpt inspections and synthetic test do not need repeating.

Use existing standing repair authorization to prepare only the private source input below. No repair application, startup/prerequisite execution or build is included. This reuses the existing scripts and artifact-review process, not a second launcher or authority service.

## Laptop prompt

```text
Prepare a PRIVATE source-only review packet from the existing blocked stage. Do not execute or modify any source script or rerun the synthetic test. No network, Firecrawl, paid service, installation, model/API call, build, owner/provisioner, registration or application-state action.

Read the complete existing files as raw bytes:
ops\enter-task.ps1 — expected 3188 bytes, SHA256 f9a1958ae123f0f7f583fa5671ce146bcdefd92a8746710fc2db631733fe2aec
ops\verify-prerequisites.ps1 — expected 15874 bytes, SHA256 4d10b3930d0c3266880750161ddd7e8eff9b1a7e5832917268254aa8904e797d

Verify both raw lengths/hashes. Mismatch, unresolved path or unexpected link: stop and report it, without changing anything or substituting another source version. Inspect as text for credentials, tokens or embedded actual environment-value dumps before packaging. If found, stop and report presence only; do not disclose them or silently redact/hash-relabel the source. Ordinary private paths may remain only in this private packet; do not publish it to GitHub or another service.

Include any necessary directly referenced existing script helpers confined to the same ops directory, as raw source only. Do not execute references, evaluate dynamic paths, traverse links or expand to unrelated files. List unresolved/dynamic/outside references explicitly as UNKNOWN. Do not include SQLite/state/cache files, transcripts, credentials, executables or unrelated inventory.

Create only a NEW exclusive sibling directory, genie-startup-review-input-20261019, in the same owned project. Existing directory means stop/preserve. Use supported New-Item -Path for directory creation, never -Force. Keep all new packet/log/archive outputs there; leave the old stage and successful diagnostic directory untouched.

Make one data-only ZIP containing README_FIRST.md (verify digest/ZIP paths/CRC/manifest before extraction; execute no subject), MANIFEST.json (exclude itself; bind every other ZIP file by exact safe relative path, raw byte length and SHA256), and complete raw scripts preserving their relative structure under source/ops/. Include a small static report listing unresolved references and all process-scoped environment-removal calls/target expressions, including PIP_* cleanup; do not change them. Mark historical executed-byte identity UNKNOWN.

Return the ZIP using one copyable JSON object with zip_sha256, zip_bytes and zip_base64. This is private text transport to this review chat, not publication. Preserve the local packet and originals. Stop after returning the packet; do not apply the proposed two-line repair or run anything from it.
```

## Subsequent eligible work

Only after safe receipt/verification of the complete private source can the exact startup correction and same-function removal inventory be reviewed together. Preserve existing absence checks and stage/build owners; distinguish process removals from value-setting and User/Machine operations. New execution needs a concrete fresh-attempt contract and the existing stopping/cost/HOLD boundaries; this source packet grants none. Private full source must not be copied into the public repair repository.

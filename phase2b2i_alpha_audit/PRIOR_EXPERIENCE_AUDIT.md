# Standing L7/L2/Genie/EXP010 correspondence audit

Classification: **ALPHA DOWNLOAD/UNPACK STATIC AUDIT ONLY - NONCLAIM**.

This audit was completed before downloading any prerelease archive.  It
transfers constraints, not authority or proof.

## L7

Registry version, dist integrity, archive hash, unpacked executable hash, and
embedded strings are identity/static-evidence bindings only.  They do not prove
runtime parsing, isolation, compatibility, or authority.  A prerelease cannot
silently replace the stable binding.

## L2

Archive download, integrity verification, unpacking, static inspection,
installation, executable launch, authentication, app-server initialization,
inventory observation, and semantic execution remain separate stages.  This
audit ends after static inspection.

## Genie

No historical terminal `UNKNOWN` is retried, reset, refunded, resumed, or
replaced.  No logical operation is created.  No executable from the archive is
run.  Any later alpha execution or installation requires separate explicit
authorization.

## EXP010

Only evidence discipline transfers: exact identities, raw archive integrity,
chronology, and explicit separation of observation from inference.  No EXP010
execution, semantics, promotion, or authority is used.

## Authorized boundary

Allowed: query exact registry metadata for `@openai/codex@0.163.0-alpha.11` and
its Windows x64 package, download exact npm archives into an isolated workspace
directory, verify integrity, unpack without lifecycle scripts, enumerate files,
hash selected files, and search static bytes/text for the documented flag.

Prohibited: npm install, package lifecycle scripts, executing the alpha binary,
login/logout, credential reads or copies, app-server startup, inventory
protocol, semantic request, worker/model execution, Genie mutation,
historical-run mutation, reviewer progression, Phase 2C, main merge,
promotion/freeze, spending beyond the already-authorized ordinary package
download, or EXP010.

Same-host and same-registry evidence remains common-cause and non-independent.

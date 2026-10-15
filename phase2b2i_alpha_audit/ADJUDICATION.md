# Adjudication

Decision: **STATIC_CANDIDATE_NONCLAIM**.

The exact Windows x64 archive matches the registry integrity value, contains
only validated regular paths, declares no package lifecycle scripts, and
contains a distinct `codex.exe` with a valid OpenAI Authenticode signature.
The documented `--ignore-user-config` literal occurs in its static bytes.

These facts make this build a candidate for one separately authorized,
offline parser-only probe.  Embedded text is not proof that the argument parser
accepts the option, and a signature is not proof of runtime isolation.

Installation, execution, process launch, app-server initialization, effective
inventory observation, authentication change, worker/model execution, and live
Phase 2B2 remain disallowed and unperformed.  Same-host and same-registry
evidence is common-cause and non-independent.

Two validation-harness attempts stopped before extraction: the first
PowerShell path check false-rejected a safe path, and the first Python check
had a control-flow error after validating one archive.  Neither attempt
extracted or executed content.  The corrected validator checked every member
of both archives before extraction.

At closeout, the installed stable executable had a different path, size, and
SHA-256 from the earlier stable baseline.  Its Authenticode signature remained
valid, while the authentication and configuration file hashes matched their
pre-audit values.  This is recorded as external state drift with no causal
claim; the audit did not install either package or execute the alpha.

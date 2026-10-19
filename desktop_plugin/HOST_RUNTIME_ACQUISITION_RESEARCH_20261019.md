# R09 runtime acquisition research — 2026-10-19, NONCLAIM

The reported frontier is PREPARATION_SEALED_BLOCKED_RUNTIME. The receipt is
`repair_validation/HOST_PREPARATION_SEAL_REPORT_20261019.json`; these are user-reported
results, not direct inspection of host manifests. Preserve all original and
corrected stages, source, evidence, seals and completed diagnostics. Do not repeat
searches or preparation already exhausted by the local operator.

The existing HOST_STAGE_PLAN_20261018.md explicitly requires a preexisting exact
CPython 3.12.10 x64 and forbids runtime download. That plan remains unchanged and
its stopped branch remains stopped. Standing repair authorization separately
forbids global installation; it does not establish that an isolated official
archive is technically suitable. An acquisition amendment must be explicit,
reviewed and recorded before a new execution branch. This research note is not
that executable amendment and does not relax a gate.

## Primary-source findings

- Python's Windows documentation describes its NuGet distribution as intended for
  build systems without a system-wide Python installation, supports exact version
  selection, identifies `python` as x64, and describes `tools/python.exe`.
  https://docs.python.org/3.12/using/windows.html#the-nuget-org-packages
- The exact gallery entry `python/3.12.10` identifies a 64-bit build runtime with no
  package dependencies and links to Python's project/source; its owners include
  CPython and steve.dower. This is package metadata, not an archive hash receipt.
  https://www.nuget.org/packages/python/3.12.10
- CPython's v3.12.10 `Tools/nuget/make_pkg.proj` selects `--preset-nuget`.
  The same tag's `PC/layout/support/options.py` includes pip, venv, headers/libs,
  stable ABI, props and nuspec in that preset. Source configuration supports
  investigating compatibility; it does not verify the downloaded archive.
  https://github.com/python/cpython/blob/v3.12.10/Tools/nuget/make_pkg.proj
  https://github.com/python/cpython/blob/v3.12.10/PC/layout/support/options.py
- The embeddable distribution omits pip, and normal pip dependency management is
  unsupported there. It is not the proposed route for this existing venv build.
  https://docs.python.org/3.12/using/windows.html#the-embeddable-package

No runtime archive was downloaded, extracted or executed by this research. No
publisher archive digest, signature status, exact archive file inventory, native
runtime identity, venv/bootstrap behavior or successful build is established.
The exact version is retained for build reproduction, not substituted with a
newer Python or presented as a general security recommendation.

## Next eligible work for the existing local repair owner

Prepare and review one narrow acquisition amendment using the above exact
package, with an exact official retrieval endpoint, redirect rules, provenance
and integrity checks, safe bounded archive inspection/extraction, and a fresh
exclusive ordinary directory. Do not introduce an installer, new package-manager
client, global/user registration, persistent PATH/config changes or a runtime
version substitution. Reject path escape, reparse/link or collision conditions;
never overwrite or clean sealed roots. Do not execute archive hooks.

Before execution, specify how the package hash and provenance are verified;
recording a newly observed digest alone is not independent publisher verification.
Determine whether the existing available signature/metadata checks are adequate,
and report any unresolved limitation honestly. Inspect exact contents for the
interpreter, architecture, standard library, ensurepip/venv and bootstrap wheels.
Do not assume a package preset proves those contents. Keep actual environment
values and private full scripts local.

Retain the corrected process-local environment handling and all existing temp,
cache, bytecode, user-site and pip controls. A narrowly reviewed runtime identity
and isolated venv/bootstrap check must precede source/dependency/build work. Use
full executable paths. Retain the exact source/tree, spec, lock union, bundled-pip
exception and no-extra-distributions gate. Missing Git, dependency/bootstrap
mismatch or uncertain process termination is a stop, not permission for a retry
or alternate toolchain. Preserve one-call probe and canonical-root gates.

This continues the existing R09 owner; no parallel bootstrap implementation or
new authority mechanism. Do not rerun completed diagnostics, pilots or scientific
work. No paid services/credits, provider/model calls, global installation, main
merge, deployment/activation, canonical state creation/migration or master-roadmap
mutation. R13's independent cost-bound/model-route HOLD remains unchanged.

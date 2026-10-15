# Isolation recovery design test results

Environment: exact accepted Phase 2A CPython 3.12.14; standard library only;
temporary test root outside the repository but inside the approved workspace.

## Authoritative clean run

The exact accepted 129-test Phase 2B2B manifest was run with the later Phase
2B2 live/recovery/isolation suites and seven new design tests:

- inherited Phase 2B2 focused/regression tests: **154/154 passed**;
- new offline isolation-design tests: **7/7 passed**;
- total: **161/161 passed, zero skips**.

The new tests prove that the bound runtime fails closed to upgrade/rebind only,
a hypothetical supported runtime still cannot authorize process entry,
credential copying is always false, authority-bearing child fields are
rejected, future isolation paths must be absolute/distinct/outside prohibited
roots, the module contains no process/copy/network capability, and no real auth
path or credential hash is serialized.

No Codex executable, model, authentication flow, credential copy, Genie MCP,
or historical run was exercised.

## Non-authoritative harness attempts

Two earlier invocations are not counted as evidence.  A default discovery run
found only the new package because historical directories are namespace-style.
A broad file-path sweep included bespoke legacy scripts that require arguments
or privileges and inherited a managed temporary directory inside the repository.
The isolation suites correctly rejected that temporary location.  Transient
test directories were deleted, the repository was clean except for this new
artifact, and the exact recorded suite manifest was then rerun successfully
with a dedicated external temporary root.

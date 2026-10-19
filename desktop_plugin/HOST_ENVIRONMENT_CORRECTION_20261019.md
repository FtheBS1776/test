# Focused PowerShell environment-removal correction — R09

This extends the existing host-stage repair. It introduces no runtime owner, launcher, cost service or roadmap. The original pinned plan, blocked attempt, host setup scripts and evidence remain unchanged. Standing repair authorization covers preparation and this focused no-model test; installation/deployment/science/model exclusions remain in force.

## Evidence and correction

The 2026-10-19 user report supplies selected current script excerpts and whole-file hashes, not the complete files or proof of historical execution. `enter-task.ps1` reportedly uses `[Environment]::SetEnvironmentVariable(name, $null, 'Process')`, then records `-not (Test-Path Env:name)`. The checker later requires actual absence and throws on false flags. PowerShell 7.6.5 was previously reported. Microsoft documents different null handling for the method and provider assignment in modern PowerShell: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables?view=powershell-7.6

The minimal proposed replacement of the reported startup fragment is:

```diff
-[Environment]::SetEnvironmentVariable('PYTHONPATH', $null, 'Process')
-[Environment]::SetEnvironmentVariable('PYTHONHOME', $null, 'Process')
+$env:PYTHONPATH = $null
+$env:PYTHONHOME = $null
+if ((Test-Path -LiteralPath Env:PYTHONPATH) -or (Test-Path -LiteralPath Env:PYTHONHOME)) {
+    throw 'BLOCKED_TASK_LOCAL_ENVIRONMENT'
+}
```

Retain the startup record and prerequisite checker's absence tests. Do not weaken them to null/empty-string checks, use Python ignore-environment flags as a bypass, or alter User/Machine settings. This is an exact fragment proposal, not a claimed complete patch of unseen host files. Do not apply it to or execute the original blocked scripts.

## Next executable scope: synthetic test only

Use the exact `desktop_plugin/test_environment_removal.ps1` reviewed with this contract. It changes only `GENIE_ENV_REMOVAL_PROBE_20261019` in one fresh existing PowerShell 7.6.5 process. It refuses an inherited name collision before mutation, reproduces the reported three-argument method with synthetic data, classifies presence/emptiness without printing values, checks provider removal and repeated-removal absence, and removes its synthetic variable in `finally`. No real Python variable, User/Machine environment, file, state, provider/model, import, child process or network operation is performed by the script itself.

The host operator may create only one NEW exclusive sibling of the old stage under the same owned project: `genie-env-removal-check-20261019`. If it exists, stop and preserve it. Never put new outputs inside the blocked stage. Save the exact test script there and capture its one invocation's stdout/stderr, real exit status, script hash/length, command and process metadata into that new directory. Use the already available PowerShell host, with `-NoLogo -NoProfile -NonInteractive -File <new-test-path>`, in a fresh process. Before starting it, use the existing child-process launch interface to set child-only `TEMP`, `TMP` and `TMPDIR` to existing ordinary temp directories in the new diagnostic directory, and `PSModuleAnalysisCachePath` to a cache-file path there. Verify resolved paths stay in that new directory; do not let inherited pointers target the old stage. Supply these overrides before PowerShell starts, without changing the parent process, profiles, User/Machine settings or either real Python variable. If the available launch interface cannot establish this child-only environment, stop BLOCKED rather than adding a launcher, changing policy or falling back to the occupied task process. These are standard launch-environment parameters, not a new persistent execution owner. If that host/path/freshness or script hash cannot be established, return BLOCKED without a test or software installation. Do not alter execution policy or use an ExecutionPolicy bypass. No persistent configuration changes.

Only an exact immutable test-file download by unauthenticated direct HTTPS or the existing GitHub connector is permitted, if a local copy is unavailable. Use no Firecrawl, search/scrape/credit service, credentials, billable source or alternative download. Compare raw SHA256/length with the delivered values before execution. Failed/unavailable retrieval stops; no fallback. The test source must remain byte-identical. Public direct source retrieval is the only permitted network preparation, not a paid-service authorization.

Require exactly one test invocation and record actual output. Expected result: exit 0 and `SYNTHETIC_SEMANTICS_CONFIRMED`, with `dotnet_null_result=PRESENT_EMPTY`, both provider absence checks true and final absence true. The script's other statuses, exceptions, timeout, unavailable runtime, collision or uncertain process termination are BLOCKED/UNKNOWN; preserve all files and stop without retry, cleanup or continuation. The initial synthetic-name collision and version gates make no variable changes. Do not fabricate a result from source reading.

The operator must not run `enter-task.ps1`, `verify-prerequisites.ps1`, clone/build/archive commands, Python/Git probes, actual environment cleanup, candidate executable/tools, owner/provisioner or any scientific/model/pilot action. Do not resume, clean, delete or modify the old stage. No package/registration/cache/canonical-state changes. This test does not authorize the next build stage or canonical first creation.

## Meaning and stopping

A successful result establishes this synthetic method/provider contrast in the observed host process. It does not prove the original variables were empty, which script bytes ran historically, the entire setup/checker is correct, prerequisites/build compatibility, complete cost containment or useful Genie operation. Historical attribution remains UNKNOWN. This is trusted-host focused testing, not hostile-host or OS-wide write confinement. OS-managed cache/log activity is outside the task-controlled write claim. The cloud has no PowerShell executable and has not run this test. Internal inference cost remains unknown; preserve the prior reported one Firecrawl credit and UNKNOWN monetary charge.

Return the raw redacted JSON/stdout/stderr, actual exit/termination, test file SHA256/bytes, observed PowerShell/.NET versions, fresh PID and any blocked/unknown reason. Stop after the report. The next eligible action after confirmation is to prepare/review a fresh-attempt startup correction against complete host source and unchanged stage/build gates; no blocked-stage reuse or full setup execution follows automatically.

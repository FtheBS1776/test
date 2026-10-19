# Directory-creation correction for the synthetic diagnostic

This addendum follows the user-reported zero-launch preparation failure. It preserves the pinned 6,693-byte contract (`6c0ef0bcabc60c561bb98f4607f7031dafa59f6b6b2423955136129d58832a6b`), 3,074-byte test (`0037d07a71414c236dced24869efc4f498841e1d89e0eb0d923a0ac84333893a`), original blocked attempt and all evidence. Neither file is changed. No new owner, launcher, roadmap or execution authority is introduced. Existing standing repair authorization covers this corrected preparation attempt; all original effect and cost limits remain.

## Verified API correction

Microsoft's PowerShell 7.6 New-Item syntax supplies `-Path`, not `-LiteralPath`. Its Path parameter has literal-path behavior. Primary source consulted 2026-10-19: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-item?view=powershell-7.6

The supplied fragment from the unseen operator preparation command has one unsupported parameter. Replace that parameter only on directory-creation New-Item calls, retaining the same intended target and other permitted arguments:

```diff
-$created = New-Item -ItemType Directory -LiteralPath $diagnosticRoot -ErrorAction Stop
+$created = Microsoft.PowerShell.Management\New-Item -ItemType Directory -Path $diagnosticRoot -ErrorAction Stop
```

The complete operator command was not supplied (the report ends in an ellipsis). This diff specifies the corrected minimal call, not an attested full-wrapper patch. Keep `-LiteralPath` on Test-Path/Get-Item and other cmdlets that support it; do not perform a global replacement. Do not add `-Force`, automatic cleanup, overwrite, fallback or error suppression. Before mutation, the existing host may read built-in New-Item command metadata to confirm the Path parameter is available; inability to establish the supported command stops the task.

## One corrected attempt, unchanged native test

Recheck the existing contract's parent/target/runtime/synthetic-name gates rather than relying on the previous report. Use the same diagnostic directory name only if it is still absent: `genie-env-removal-check-20261019`, a new exclusive sibling of the original blocked stage in the same owned project. Any existing target, unresolved/link condition, failed or uncertain check stops and preserves it. Do not reuse an occupied directory or write inside the old stage. The user reported the failed parameter binding created no directory/file and started no test; that historical attempt stays recorded as BLOCKED, invocation count zero.

Use the pinned bytes already available only after raw hash/length verification. If unavailable, acquire the same exact immutable files using only the original direct unauthenticated HTTPS/GitHub route. No Firecrawl, credit-consuming service, paid API, credentials or fallback source.

With the corrected directory call and all original gates satisfied, perform exactly the original one fresh-process synthetic-only diagnostic. Keep the contract's child-only prelaunch temp/cache settings in the new directory, existing PowerShell 7.6.5 host, no parent/real-Python environment changes, no policy bypass and actual stdout/stderr/exit/termination capture. Do not run the old setup/check scripts, build, clone, install, provision or invoke Genie/model/science/pilot work.

Stop after the actual report, including success. Any preparation or launch failure/unknown stops without another retry, deletion or continuation. This is a separately prepared correction following the recorded stop, not an automatic retry loop or permission to bypass a failed gate. No full setup/build action follows.

## Evidence limits

The error concerns operator preparation and says nothing about the unstarted synthetic test's outcome. Microsoft documentation establishes the parameter contract; it is not a native directory-creation or environment-removal pass. The cloud has not run PowerShell. Prior static reviews retain only their original exact code/contract scope and do not attest to the unseen preparation wrapper. The normalized report is `repair_validation/HOST_ENVIRONMENT_DIRECTORY_BLOCKER_20261019.json`. Historical evidence, governance/HOLD, no main merge, deployment, master mutation, installation and cost boundaries remain unchanged.

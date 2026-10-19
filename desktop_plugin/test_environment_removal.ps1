# Focused host diagnostic only. Run once in a fresh existing PowerShell 7.6.5
# process, with -NoLogo -NoProfile -NonInteractive. No imports or child launches.
# Changes only one synthetic process variable. Does not repair/resume a stage.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$probePath = 'Env:GENIE_ENV_REMOVAL_PROBE_20261019'
if ($PSVersionTable.PSVersion.ToString() -ne '7.6.5') {
    [ordered]@{ status = 'BLOCKED_POWERSHELL_VERSION'; powershell = $PSVersionTable.PSVersion.ToString() } | ConvertTo-Json -Compress
    exit 2
}
if (Test-Path -LiteralPath $probePath) {
    [ordered]@{ status = 'BLOCKED_SYNTHETIC_NAME_PRESENT' } | ConvertTo-Json -Compress
    exit 2
}

$record = [ordered]@{
    status = 'UNKNOWN'
    powershell = $PSVersionTable.PSVersion.ToString()
    dotnet = [System.Runtime.InteropServices.RuntimeInformation]::FrameworkDescription
    process_id = $PID
    dotnet_seeded = $false
    dotnet_null_result = 'NOT_REACHED'
    provider_seeded = $false
    provider_absent = $false
    provider_idempotent_absent = $false
    final_absent = $false
    error_kind = $null
}
try {
    $env:GENIE_ENV_REMOVAL_PROBE_20261019 = 'GENIE_SYNTHETIC_SENTINEL'
    $record.dotnet_seeded = (Test-Path -LiteralPath $probePath) -and (([string](Get-Item -LiteralPath $probePath).Value) -ceq 'GENIE_SYNTHETIC_SENTINEL')
    if (-not $record.dotnet_seeded) { throw 'SYNTHETIC_SEED_FAILED' }
    [Environment]::SetEnvironmentVariable('GENIE_ENV_REMOVAL_PROBE_20261019', $null, 'Process')
    if (Test-Path -LiteralPath $probePath) {
        if (([string](Get-Item -LiteralPath $probePath).Value).Length -eq 0) {
            $record.dotnet_null_result = 'PRESENT_EMPTY'
        } else {
            $record.dotnet_null_result = 'PRESENT_NONEMPTY'
        }
    } else {
        $record.dotnet_null_result = 'ABSENT'
    }

    $env:GENIE_ENV_REMOVAL_PROBE_20261019 = 'GENIE_SYNTHETIC_SENTINEL'
    $record.provider_seeded = (Test-Path -LiteralPath $probePath) -and (([string](Get-Item -LiteralPath $probePath).Value) -ceq 'GENIE_SYNTHETIC_SENTINEL')
    if (-not $record.provider_seeded) { throw 'SYNTHETIC_SEED_FAILED' }
    $env:GENIE_ENV_REMOVAL_PROBE_20261019 = $null
    $record.provider_absent = -not (Test-Path -LiteralPath $probePath)
    $env:GENIE_ENV_REMOVAL_PROBE_20261019 = $null
    $record.provider_idempotent_absent = -not (Test-Path -LiteralPath $probePath)

    if (($record.dotnet_null_result -eq 'PRESENT_EMPTY') -and $record.provider_absent -and $record.provider_idempotent_absent) {
        $record.status = 'SYNTHETIC_SEMANTICS_CONFIRMED'
    } else {
        $record.status = 'UNEXPECTED_SEMANTICS'
    }
} catch {
    $record.status = 'UNKNOWN'
    $record.error_kind = $_.Exception.GetType().FullName
} finally {
    $env:GENIE_ENV_REMOVAL_PROBE_20261019 = $null
    $record.final_absent = -not (Test-Path -LiteralPath $probePath)
}
if (-not $record.final_absent) {
    $record.status = 'UNKNOWN'
}
$record | ConvertTo-Json -Depth 3 -Compress
if ($record.status -eq 'SYNTHETIC_SEMANTICS_CONFIRMED') { exit 0 }
exit 2

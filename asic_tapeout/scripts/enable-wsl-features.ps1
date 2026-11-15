# ASIC Stage 0C — enable Microsoft's two prerequisite WSL2 Windows features.
# Run from an elevated Windows PowerShell. No automatic restart, distro install, reset or deletion.
# This changes WINDOWS OPTIONAL FEATURES (Windows system files are on C:).
# Only development output written by this script is a log in G:\C-Drive-Backup-PreReset\Temp.
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
if (!(Test-Path -LiteralPath $root -PathType Container)) {
    Write-Host 'FAIL | G: project root not found; nothing changed'
    return
}
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host 'FAIL | Start Windows PowerShell as Administrator; nothing changed'
    return
}
$dir = Join-Path $root 'Temp'
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$log = Join-Path $dir ('ASIC-WSL-Enable-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$results = New-Object 'System.Collections.Generic.List[string]'
function Report([System.Collections.Generic.List[string]]$buffer,[string]$state,[string]$label,[string]$details) {
    $line = "$state | $label | $details"
    Write-Host $line
    [void]$buffer.Add($line)
}
Write-Host '===== ASIC STAGE 0C: ENABLE WSL2 PREREQUISITES ====='
$fail = 0
$restartNeeded = $false
$features = @('Microsoft-Windows-Subsystem-Linux','VirtualMachinePlatform')
foreach ($feature in $features) {
    try {
        $current = (Get-WindowsOptionalFeature -Online -FeatureName $feature -ErrorAction Stop).State.ToString()
        if ($current -eq 'Enabled') {
            Report $results PASS $feature 'already enabled'
        } elseif ($current -eq 'EnablePending') {
            $restartNeeded = $true
            Report $results PASS $feature 'enable pending; reboot required'
        } elseif ($current -ne 'Disabled') {
            $fail++
            Report $results FAIL $feature "unexpected state $current; not modified"
        } else {
            Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart -ErrorAction Stop | Out-Null
            $after = (Get-WindowsOptionalFeature -Online -FeatureName $feature -ErrorAction Stop).State.ToString()
            if ($after -in @('Enabled','EnablePending')) {
                $restartNeeded = $true
                Report $results PASS $feature "feature enabled; reported state: $after"
            } else {
                $fail++
                Report $results FAIL $feature "unexpected state after enabling: $after"
            }
        }
    } catch {
        $fail++
        Report $results FAIL $feature $_.Exception.Message
    }
}
if ($fail -eq 0) {
    Report $results PASS 'Feature setup' 'both prerequisites enabled or awaiting reboot'
    Report $results INFO 'Next action' $(if ($restartNeeded) {'RESTART Windows manually, then recheck WSL'} else {'No reboot requested by this script; recheck WSL'})
} else {
    Report $results WARN 'Feature setup' "$fail checks failed; review log BEFORE restart or additional repairs"
}
[void]$results.Add('No Linux distribution was created, imported, registered, reset, unregistered or deleted.')
[void]$results.Add('No Git, Docker or EDA software was installed.')
$results | Out-File -LiteralPath $log -Encoding UTF8
Write-Host "INFO | Full log: $log"
Write-Host '===== END ASIC STAGE 0C ====='
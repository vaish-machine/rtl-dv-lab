# ASIC Stage 0D — read-only WSL post-restart verification.
# Only new file is a log under G:\C-Drive-Backup-PreReset\Temp.
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    Write-Host 'FAIL | G: development root unavailable; nothing changed'
    return
}
$dir = Join-Path $root 'Temp'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$log = Join-Path $dir ('ASIC-WSL-Runtime-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$lines = New-Object 'System.Collections.Generic.List[string]'
function Report([System.Collections.Generic.List[string]]$buffer,[string]$state,[string]$label,[string]$detail) {
    $line = "$state | $label | $detail"
    Write-Host $line
    [void]$buffer.Add($line)
}
Write-Host '===== ASIC STAGE 0D: WSL RUNTIME VERIFICATION ====='
foreach ($feature in @('Microsoft-Windows-Subsystem-Linux','VirtualMachinePlatform')) {
    try {
        $state = (Get-WindowsOptionalFeature -Online -FeatureName $feature -ErrorAction Stop).State.ToString()
        Report $lines $(if ($state -eq 'Enabled') {'PASS'} else {'WARN'}) $feature $state
    } catch {
        Report $lines WARN $feature ('feature read unavailable: ' + $_.Exception.Message)
    }
}
$pending = $false
foreach ($reg in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending','HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')) {
    if (Test-Path -LiteralPath $reg) { $pending = $true }
}
Report $lines $(if($pending){'WARN'}else{'INFO'}) 'Pending Windows reboot' $(if($pending){'detected; restart before further repair'}else{'none in checked registry keys'})
$wslExe = Join-Path $env:SystemRoot 'System32\wsl.exe'
if (-not (Test-Path -LiteralPath $wslExe -PathType Leaf)) {
    Report $lines FAIL 'WSL executable' 'not present in Windows System32'
} elseif ($pending) {
    Report $lines WARN 'WSL commands' 'skipped because reboot is pending'
} else {
    foreach ($entry in @(
        @{Label='WSL version'; Args=@('--version')},
        @{Label='WSL status'; Args=@('--status')},
        @{Label='Registered distributions'; Args=@('--list','--verbose')}
    )) {
        try {
            # External command output may go to stderr even for normal status messages.
            $commandArgs = [string[]]$entry.Args
            $output = & $wslExe @commandArgs 2>&1 | Out-String
            $exit = $LASTEXITCODE
            $detail = ($output -replace '\s+',' ').Trim()
            if ([string]::IsNullOrWhiteSpace($detail)) { $detail = '(no output)' }
            if ($detail.Length -gt 300) { $detail = $detail.Substring(0,300) + '...' }
            Report $lines $(if ($exit -eq 0) {'PASS'} else {'WARN'}) $entry.Label "exit=$exit; $detail"
        } catch {
            Report $lines WARN $entry.Label $_.Exception.Message
        }
    }
}
[void]$lines.Add('No WSL distribution install, update, reset, unregister or repair was performed.')
$lines | Out-File -LiteralPath $log -Encoding UTF8
Write-Host "INFO | Detailed log: $log"
Write-Host '===== END ASIC STAGE 0D ====='
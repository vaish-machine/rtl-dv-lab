# ASIC Stage 0F-DIAG: read-only checks for failed Ubuntu install-script WSL preflight.
# Does NOT install, update, unregister, reset, or delete any WSL distribution.
# Only writes a text report under G:\C-Drive-Backup-PreReset\Temp.
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    Write-Host 'FAIL | G: project root missing; no changes made'
    return
}
$dir = Join-Path $root 'Temp'
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$log = Join-Path $dir ('ASIC-Stage0F-Diagnostic-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$lines = New-Object 'System.Collections.Generic.List[string]'
function Report([System.Collections.Generic.List[string]]$buffer,[string]$state,[string]$name,[string]$detail) {
    $line = "$state | $name | $detail"
    Write-Host $line
    [void]$buffer.Add($line)
}
function Invoke-WslProbe([string[]]$WslArgs) {
    $exe = Join-Path $env:WINDIR 'System32\wsl.exe'
    $prior = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $exe @WslArgs 2>&1 | Out-String
        $exit = $LASTEXITCODE
        return [pscustomobject]@{ ExitCode=$exit; OutputText=[string]$raw }
    } finally {
        $ErrorActionPreference = $prior
    }
}
Write-Host '===== ASIC STAGE 0F: PREFLIGHT DIAGNOSIS ====='
try {
    Report $lines INFO 'PowerShell version' "$($PSVersionTable.PSVersion)"
    Report $lines INFO 'PowerShell 64-bit' "$([Environment]::Is64BitProcess)"
    $wsl = Join-Path $env:WINDIR 'System32\wsl.exe'
    if (-not (Test-Path -LiteralPath $wsl -PathType Leaf)) { throw "WSL executable missing: $wsl" }
    Report $lines PASS 'WSL executable' $wsl
    $v = Invoke-WslProbe -WslArgs @('--version')
    $vText = ($v.OutputText -replace '\u0000','' -replace '\s+',' ').Trim()
    $vShort = if ($vText.Length -gt 250) {$vText.Substring(0,250)} else {$vText}
    Report $lines $(if($v.ExitCode -eq 0 -and $vText -match 'WSL version'){'PASS'}else{'WARN'}) 'WSL version' "exit=$($v.ExitCode); chars=$($v.OutputText.Length); text=$vShort"
    $locations = @(
        (Join-Path $root 'DevTools\WSL\Ubuntu-24.04'),
        (Join-Path $root 'DevTools\WSL')
    )
    foreach ($location in $locations) {
        Report $lines INFO "Directory $location" $(if(Test-Path -LiteralPath $location){'exists; inspect before retrying installation'}else{'absent'})
    }
    $l = Invoke-WslProbe -WslArgs @('--list','--verbose')
    $lText = ($l.OutputText -replace '\u0000','' -replace '\s+',' ').Trim()
    $lShort = if($lText.Length -gt 250){$lText.Substring(0,250)}else{$lText}
    Report $lines INFO 'WSL distributions' "exit=$($l.ExitCode); text=$lShort"
    $h = Invoke-WslProbe -WslArgs @('--install','--help')
    $hText = ($h.OutputText -replace '\u0000','' -replace '\s+',' ').Trim()
    Report $lines $(if($hText -match '--location'){'PASS'}else{'WARN'}) 'WSL --location support' "exit=$($h.ExitCode); found=$($hText -match '--location'); chars=$($hText.Length)"
} catch {
    Report $lines FAIL 'Diagnostic' $_.Exception.Message
} finally {
    [void]$lines.Add('Read-only diagnosis. No WSL/Git/Ubuntu installation or repair attempted.')
    $lines | Out-File -LiteralPath $log -Encoding UTF8
    Write-Host "INFO | Detailed log: $log"
    Write-Host '===== END ASIC STAGE 0F DIAGNOSIS ====='
}
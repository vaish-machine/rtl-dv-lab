# ASIC Stage 0G — first launch of Ubuntu 24.04 and read-only account verification.
# Creates Linux user/password only through Ubuntu's own interactive first-run prompts.
# Never prints/stores passwords. Only writes summary diagnostics under G:\...\Temp.
# Run from the normal Windows account that owns the WSL distro.
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
$location = Join-Path $root 'DevTools\WSL\Ubuntu-24.04'
$vhd = Join-Path $location 'ext4.vhdx'
if(-not (Test-Path -LiteralPath $vhd -PathType Leaf)) {
    Write-Host 'FAIL | Expected G: Ubuntu disk missing. Do not reinstall or initialize blindly.'
    return
}
$dir = Join-Path $root 'Temp'
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$log = Join-Path $dir ('ASIC-Ubuntu-FirstLaunch-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$lines = New-Object 'System.Collections.Generic.List[string]'
function Report([System.Collections.Generic.List[string]]$buffer,[string]$status,[string]$name,[string]$value) {
    $line = "$status | $name | $value"
    Write-Host $line
    [void]$buffer.Add($line)
}
Write-Host '===== ASIC STAGE 0G: UBUNTU FIRST LAUNCH ====='
$wsl = Join-Path $env:WINDIR 'System32\wsl.exe'
try {
    $available = & $wsl --list --quiet 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0 -or $available -notmatch 'Ubuntu-24\.04') {
        throw 'Ubuntu-24.04 is not listed; stopping without touching the distribution'
    }
    Report $lines PASS 'Ubuntu registration' 'Ubuntu-24.04 listed'
    Report $lines PASS 'Persistent disk' $vhd
    Report $lines INFO 'First launch' 'If prompted, choose a new Linux username/password; passwords will not appear as you type'
    Report $lines INFO 'Leave Ubuntu shell' 'After successful creation type exit, then PowerShell verifies the account'
    # Direct invocation preserves interactive console so no password is captured.
    & $wsl -d Ubuntu-24.04
    $exit = $LASTEXITCODE
    if ($exit -ne 0) {
        throw "Ubuntu first launch returned exit=$exit; account not verified"
    }
    $user = & $wsl -d Ubuntu-24.04 --exec id -un 2>&1 | Out-String
    $userExit = $LASTEXITCODE
    $uid = & $wsl -d Ubuntu-24.04 --exec id -u 2>&1 | Out-String
    $uidExit = $LASTEXITCODE
    $os = & $wsl -d Ubuntu-24.04 --exec cat /etc/os-release 2>&1 | Out-String
    $osExit = $LASTEXITCODE
    $user = ($user -replace '\x00','').Trim()
    $uid = ($uid -replace '\x00','').Trim()
    if ($userExit -ne 0 -or $uidExit -ne 0 -or $osExit -ne 0) {
        throw 'Ubuntu launched, but identity/OS checks failed; inspect Ubuntu before installing tools'
    }
    if ($uid -eq '0') {
        Report $lines WARN 'Default Linux account' 'root (UID 0); normal-user creation/configuration not confirmed'
    } else {
        Report $lines PASS 'Non-root Linux user' "$user (UID $uid)"
    }
    Report $lines $(if($os -match 'VERSION_ID="24.04"'){'PASS'}else{'WARN'}) 'Ubuntu release' $(if($os -match 'VERSION_ID="24.04"'){'24.04'}else{'not confirmed'})
    Report $lines INFO 'Git and ASIC tools' 'Not installed by this script'
} catch {
    Report $lines FAIL 'First launch or verification' $_.Exception.Message
} finally {
    [void]$lines.Add('This script never captures Linux passwords; it does not install packages or modify existing project files.')
    $lines | Out-File -LiteralPath $log -Encoding UTF8
    Write-Host "INFO | Detailed log: $log"
    Write-Host '===== END ASIC STAGE 0G ====='
}
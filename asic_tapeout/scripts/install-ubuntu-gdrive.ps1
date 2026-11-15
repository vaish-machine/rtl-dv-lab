# ASIC Stage 0F — install Ubuntu 24.04 LTS WSL2 on G: using Microsoft's --location option.
# Changes: installs one Ubuntu distribution and stores its persistent virtual disk under G:.
# Does not reset/unregister existing distributions, install Git/EDA/Docker, or modify other projects.
# Run as the regular Windows account that will use WSL (administrator is not required).
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    Write-Host 'FAIL | G: development root missing; nothing changed'
    return
}
$logDir = Join-Path $root 'Temp'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir ('ASIC-Ubuntu24-Install-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$logLines = New-Object 'System.Collections.Generic.List[string]'
function Record([System.Collections.Generic.List[string]]$buffer,[string]$state,[string]$label,[string]$detail) {
    $line = "$state | $label | $detail"
    Write-Host $line
    [void]$buffer.Add($line)
}
function Run-Wsl([string[]]$arguments) {
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & "$env:WINDIR\System32\wsl.exe" @arguments 2>&1 | Out-String
        return @{ Exit = $LASTEXITCODE; Output = $output }
    } finally {
        $ErrorActionPreference = $prev
    }
}
Write-Host '===== ASIC STAGE 0F: UBUNTU 24.04 ON G: ====='
try {
    $destination = Join-Path $root 'DevTools\WSL\Ubuntu-24.04'
    if (Test-Path -LiteralPath $destination) {
        throw "Destination already exists; refusing to overwrite: $destination"
    }
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='G:'"
    if ($null -eq $disk -or ([double]$disk.FreeSpace / 1GB) -lt 25) {
        throw 'G: needs at least 25 GB free for this initial setup'
    }
    $freeGB = [math]::Round([double]$disk.FreeSpace / 1GB,1)
    Record $logLines PASS 'G: free GB' "$freeGB"
    $version = Run-Wsl -arguments @('--version')
    if($version.Exit -ne 0 -or $version.Output -notmatch 'WSL version') {
        throw 'WSL version command did not succeed; do not install a distro'
    }
    Record $logLines PASS 'WSL runtime' (($version.Output -replace '\s+',' ').Trim().Substring(0,[math]::Min(95,($version.Output -replace '\s+',' ').Trim().Length)))
    $help = Run-Wsl -arguments @('--install','--help')
    if ($help.Output -notmatch '--location') { throw 'This WSL installation does not advertise --location; refusing C: fallback' }
    Record $logLines PASS 'Custom install location' '--location available'
    $installed = Run-Wsl -arguments @('--list','--verbose')
    if ($installed.Exit -eq 0) {
        Record $logLines WARN 'Existing distributions' (($installed.Output -replace '\s+',' ').Trim())
        throw 'An existing distro is detected. No new installation attempted'
    }
    if ($installed.Output -notmatch '(?i)no installed distributions') {
        throw 'Unable to prove no existing distributions; refusing installation'
    }
    Record $logLines PASS 'Existing distributions' 'none, confirmed'
    $online = Run-Wsl -arguments @('--list','--online')
    if ($online.Exit -ne 0 -or $online.Output -notmatch 'Ubuntu-24\.04') {
        throw 'Ubuntu-24.04 not found in WSL online catalog; no installation attempted'
    }
    Record $logLines PASS 'Ubuntu availability' 'Ubuntu-24.04 in official WSL catalog'
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Record $logLines INFO 'Install target' $destination
    Record $logLines INFO 'Installer' 'Downloading and installing Ubuntu 24.04 LTS; --no-launch'
    $setup = Run-Wsl -arguments @('--install','--distribution','Ubuntu-24.04','--location',$destination,'--web-download','--no-launch')
    [void]$logLines.Add('WSL installer full output:')
    [void]$logLines.Add($setup.Output)
    if ($setup.Exit -ne 0) {
        throw "WSL installer exit code $($setup.Exit). Inspect detailed log; do not reinstall over existing files"
    }
    Record $logLines PASS 'WSL installer' 'Exit 0'
    $after = Run-Wsl -arguments @('--list','--verbose')
    [void]$logLines.Add('Post-install distro listing:')
    [void]$logLines.Add($after.Output)
    if ($after.Exit -eq 0 -and $after.Output -match 'Ubuntu-24\.04' -and $after.Output -match '\s2(\s|$)') {
        Record $logLines PASS 'Ubuntu 24.04 registration' 'WSL2 registered'
    } else {
        Record $logLines WARN 'Ubuntu registration' 'Installer completed but WSL2 registration not verified; inspect log'
    }
    $vhd = Join-Path $destination 'ext4.vhdx'
    Record $logLines $(if(Test-Path -LiteralPath $vhd){'PASS'}else{'INFO'}) 'Virtual disk on G:' $(if(Test-Path -LiteralPath $vhd){$vhd}else{'ext4.vhdx not at expected immediate path; inspect directory if necessary'})
    Record $logLines INFO 'Next step' 'Initialize Linux user with wsl -d Ubuntu-24.04 after reviewing the result'
} catch {
    Record $logLines FAIL 'Installation or preflight' $_.Exception.Message
} finally {
    [void]$logLines.Add('No existing WSL distro was unregistered, reset, or deleted by this script.')
    [void]$logLines.Add('No Git/EDA software was installed by this script.')
    $logLines | Out-File -LiteralPath $logPath -Encoding UTF8
    Write-Host "INFO | Detailed log: $logPath"
    Write-Host '===== END STAGE 0F ====='
}
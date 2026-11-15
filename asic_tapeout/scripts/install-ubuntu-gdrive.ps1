# ASIC Stage 0F (corrected) — install Ubuntu 24.04 LTS WSL2 directly under G:.
# Installs exactly one distro; no reset, unregister, delete, Git, Docker or EDA install.
# Always run under the Windows account that will own/use the Ubuntu distribution.
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
$destination = Join-Path $root 'DevTools\WSL\Ubuntu-24.04'
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    Write-Host 'FAIL | G: root not found; no changes made'
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
function Invoke-Wsl([string[]]$WslArgs) {
    $exe = Join-Path $env:WINDIR 'System32\wsl.exe'
    $oldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $exe @WslArgs 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
        $clean = [regex]::Replace([string]$raw,'\x00','')
        return [pscustomobject]@{
            ExitCode = $exitCode
            Raw = [string]$raw
            Text = $clean
        }
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}
function ShortText([string]$value) {
    $compact = ($value -replace '\s+',' ').Trim()
    if($compact.Length -gt 220) { return $compact.Substring(0,220) + '...' }
    return $compact
}
Write-Host '===== ASIC STAGE 0F: UBUNTU 24.04 ON G: ====='
try {
    if (Test-Path -LiteralPath $destination) {
        throw "Target exists; refusing overwrite: $destination"
    }
    $gDisk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='G:'"
    if ($null -eq $gDisk) { throw 'G: disk could not be inspected' }
    $freeGB = [math]::Round([double]$gDisk.FreeSpace / 1GB,1)
    if ($freeGB -lt 25) { throw "Insufficient G: space ($freeGB GB); 25 GB minimum" }
    Record $logLines PASS 'G: free space' "$freeGB GB"
    $wslExe = Join-Path $env:WINDIR 'System32\wsl.exe'
    if (-not (Test-Path -LiteralPath $wslExe -PathType Leaf)) { throw "WSL executable missing: $wslExe" }
    $ver = Invoke-Wsl -WslArgs @('--version')
    if ($ver.ExitCode -ne 0 -or $ver.Text -notmatch '(?i)WSL\s+version\s*:') {
        Record $logLines WARN 'WSL version details' ("exit=$($ver.ExitCode); " + (ShortText $ver.Text))
        throw 'WSL runtime did not report a usable version; install not attempted'
    }
    Record $logLines PASS 'WSL runtime' ("exit=0; " + (ShortText $ver.Text))
    # Microsoft documents capabilities with: wsl --help (not "wsl --install --help").
    $help = Invoke-Wsl -WslArgs @('--help')
    if ($help.Text -notmatch '(?i)--location') {
        Record $logLines WARN 'WSL help details' ("exit=$($help.ExitCode); " + (ShortText $help.Text))
        throw 'WSL top-level help does not advertise --location; refusing C: fallback'
    }
    Record $logLines PASS 'Custom G: location' 'wsl --help advertises --location'
    $listed = Invoke-Wsl -WslArgs @('--list','--verbose')
    [void]$logLines.Add('Pre-install WSL listing: ' + $listed.Text)
    if ($listed.ExitCode -eq 0) {
        throw 'At least one distro may be installed; review existing distros before creating another'
    }
    if ($listed.Text -notmatch '(?i)no installed distributions') {
        throw ("Existing distro state ambiguous: " + (ShortText $listed.Text))
    }
    Record $logLines PASS 'Existing distros' 'none reported'
    $catalog = Invoke-Wsl -WslArgs @('--list','--online')
    [void]$logLines.Add('WSL online distro catalog: ' + $catalog.Text)
    if ($catalog.ExitCode -ne 0 -or $catalog.Text -notmatch '(?im)Ubuntu-24\.04') {
        Record $logLines WARN 'Online catalog' ("exit=$($catalog.ExitCode); " + (ShortText $catalog.Text))
        throw 'Ubuntu-24.04 could not be confirmed in the official WSL catalog'
    }
    Record $logLines PASS 'Ubuntu-24.04 availability' 'listed online'
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Record $logLines INFO 'Install target' $destination
    Record $logLines INFO 'Install action' 'WSL Ubuntu 24.04 via --web-download --no-launch --location'
    $install = Invoke-Wsl -WslArgs @('--install','--distribution','Ubuntu-24.04','--location',$destination,'--web-download','--no-launch')
    [void]$logLines.Add('WSL install output: ' + $install.Text)
    if ($install.ExitCode -ne 0) {
        throw ("WSL installation exited $($install.ExitCode): " + (ShortText $install.Text) + '. Do NOT rerun before reviewing destination and log')
    }
    Record $logLines PASS 'WSL installer' 'Exit 0'
    $post = Invoke-Wsl -WslArgs @('--list','--verbose')
    [void]$logLines.Add('Post-install listing: ' + $post.Text)
    if ($post.ExitCode -eq 0 -and $post.Text -match 'Ubuntu-24\.04') {
        Record $logLines PASS 'Ubuntu registration' 'Ubuntu-24.04 present'
        if ($post.Text -match '(?m)Ubuntu-24\.04[^\r\n]*\s2\s*$') {
            Record $logLines PASS 'Ubuntu WSL version' '2'
        } else {
            Record $logLines WARN 'Ubuntu WSL version' 'Could not confirm WSL2 from listing; inspect log'
        }
    } else {
        Record $logLines WARN 'Ubuntu registration' 'Install exited 0 but listing is unclear; inspect log'
    }
    $vhd = Join-Path $destination 'ext4.vhdx'
    Record $logLines $(if(Test-Path -LiteralPath $vhd -PathType Leaf){'PASS'}else{'WARN'}) 'G: virtual disk' $(if(Test-Path -LiteralPath $vhd -PathType Leaf){$vhd}else{'VHDX not located at expected path'})
    Record $logLines INFO 'Next step' 'Review results; then initialize Ubuntu user'
} catch {
    Record $logLines FAIL 'Installation or preflight' $_.Exception.Message
} finally {
    [void]$logLines.Add('No existing WSL distribution was reset, unregistered, deleted or moved by this script.')
    [void]$logLines.Add('No Git, Docker, or EDA tools installed.')
    $logLines | Out-File -LiteralPath $logPath -Encoding UTF8
    Write-Host "INFO | Detailed log: $logPath"
    Write-Host '===== END STAGE 0F ====='
}
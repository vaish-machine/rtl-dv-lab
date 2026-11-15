# ASIC Stage 0E: Repair WSL using current stable Microsoft WSL release x64 MSI.
# Run from Windows PowerShell as Administrator. Alters installed WSL software.
# Does NOT unregister, remove, import, overwrite, or reset Linux distributions.
# Downloads only to G:\C-Drive-Backup-PreReset\Installers\WSL.
# MSI diagnostic logs only to G:\C-Drive-Backup-PreReset\Temp.
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    Write-Host 'FAIL | G: development root missing; nothing changed'
    return
}
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host 'FAIL | Run PowerShell as Administrator; nothing changed'
    return
}
if (-not [Environment]::Is64BitOperatingSystem) {
    Write-Host 'FAIL | Script requires x64 Windows; nothing changed'
    return
}
$installerDir = Join-Path $root 'Installers\WSL'
$logDir = Join-Path $root 'Temp'
New-Item -ItemType Directory -Force -Path $installerDir,$logDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$reportPath = Join-Path $logDir ("ASIC-WSL-MSI-Repair-$stamp.summary.log")
$msiLog = Join-Path $logDir ("ASIC-WSL-MSI-Repair-$stamp.verbose.log")
$records = New-Object 'System.Collections.Generic.List[string]'
function Log([System.Collections.Generic.List[string]]$buffer,[string]$state,[string]$label,[string]$details) {
    $line = "$state | $label | $details"
    Write-Host $line
    [void]$buffer.Add($line)
}
Write-Host '===== ASIC STAGE 0E: OFFICIAL WSL MSI REPAIR ====='
$msiStarted = $false
try {
    foreach ($name in @('Microsoft-Windows-Subsystem-Linux','VirtualMachinePlatform')) {
        $state = (Get-WindowsOptionalFeature -Online -FeatureName $name -ErrorAction Stop).State.ToString()
        if ($state -ne 'Enabled') { throw "Feature $name is $state; enable and reboot first" }
        Log $records PASS $name 'Enabled'
    }
    $pkg = @(Get-AppxPackage -Name 'MicrosoftCorporationII.WindowsSubsystemForLinux' -ErrorAction SilentlyContinue)
    $existingVersion = [version]'0.0'
    if($pkg.Count -gt 0) {
        $existingVersion = [version](($pkg | Sort-Object Version -Descending | Select-Object -First 1).Version.ToString())
    }
    Log $records INFO 'WSL app registered version' "$existingVersion"
    $nativeExe = Join-Path $env:ProgramFiles 'WSL\wsl.exe'
    Log $records INFO 'WSL native executable' $(if(Test-Path -LiteralPath $nativeExe -PathType Leaf){'present'}else{'missing'})
    $ghHeaders = @{ 'User-Agent'='ASIC-WSL-Repair'; 'Accept'='application/vnd.github+json' }
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/microsoft/WSL/releases/latest' -Headers $ghHeaders -TimeoutSec 60
    if (-not $release.tag_name -or $release.prerelease -or $release.draft) {
        throw 'Latest GitHub release metadata is unsuitable'
    }
    $releaseVersion = [version](($release.tag_name.ToString()) -replace '^v','')
    Log $records INFO 'Official latest stable WSL release' "$releaseVersion"
    if ($releaseVersion -lt $existingVersion) {
        throw "Refusing to downgrade WSL from $existingVersion to $releaseVersion"
    }
    $assets = @($release.assets | Where-Object { $_.name -match '^wsl\.\d+\.\d+\.\d+(?:\.\d+)?\.x64\.msi$' })
    if ($assets.Count -ne 1) { throw "Expected exactly one official x64 MSI, found $($assets.Count)" }
    $asset = $assets[0]
    $expectedPrefix = ('https://github.com/microsoft/WSL/releases/download/' + $release.tag_name + '/')
    if (-not $asset.browser_download_url.StartsWith($expectedPrefix,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Official release asset URL did not match microsoft/WSL'
    }
    if ($asset.digest -notmatch '^sha256:([a-fA-F0-9]{64})$') {
        throw 'Missing official GitHub SHA256 asset digest'
    }
    $expectedHash = $Matches[1].ToUpperInvariant()
    $msi = Join-Path $installerDir $asset.name
    if(Test-Path -LiteralPath $msi -PathType Leaf) {
        $currentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $msi).Hash.ToUpperInvariant()
        if($currentHash -ne $expectedHash) {
            throw "Existing MSI hash does not match the official digest: $msi (refusing overwrite)"
        }
        Log $records PASS 'Existing official MSI' 'SHA256 matches; reused installer'
    } else {
        Log $records INFO 'Download' "Downloading official Microsoft WSL MSI to $msi"
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $msi -UseBasicParsing -TimeoutSec 600
    }
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $msi).Hash.ToUpperInvariant()
    if ($actualHash -ne $expectedHash) { throw 'MSI SHA256 verification failed; installation not attempted' }
    Log $records PASS 'GitHub SHA256' 'Verified'
    $sig = Get-AuthenticodeSignature -LiteralPath $msi
    if ($sig.Status -ne 'Valid' -or $null -eq $sig.SignerCertificate -or $sig.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
        throw "MSI Authenticode signature invalid or signer unexpected: $($sig.Status)"
    }
    Log $records PASS 'Microsoft signature' $sig.SignerCertificate.Subject
    Log $records INFO 'MSI install' 'Starting in-place WSL install/repair; no distro removal'
    $arguments = @('/i',('"' + $msi + '"'),'/qn','/norestart','/L*V',('"' + $msiLog + '"'))
    $msiStarted = $true
    $proc = Start-Process -FilePath 'msiexec.exe' -ArgumentList $arguments -Wait -PassThru
    $exitCode = $proc.ExitCode
    if ($exitCode -eq 0) {
        Log $records PASS 'MSI installation' 'Exit 0, completed; WSL runtime still requires verification'
    } elseif ($exitCode -eq 3010) {
        Log $records WARN 'MSI installation' 'Exit 3010, success but restart required'
    } else {
        Log $records FAIL 'MSI installation' "Exit $exitCode; see MSI verbose log"
    }
} catch {
    Log $records FAIL 'WSL repair' $_.Exception.Message
} finally {
    [void]$records.Add('No Linux distribution or existing project files were removed.')
    [void]$records.Add('No Git, Ubuntu, Docker, or EDA software was installed by this script.')
    $records | Out-File -LiteralPath $reportPath -Encoding UTF8
    Write-Host "INFO | Summary log: $reportPath"
    if($msiStarted){ Write-Host "INFO | Installer verbose log: $msiLog" }
    Write-Host '===== END ASIC STAGE 0E ====='
}
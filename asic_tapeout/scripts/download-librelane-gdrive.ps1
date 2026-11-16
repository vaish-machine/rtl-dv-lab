# ASIC Stage 2A — download and cryptographically verify the official LibreLane
# x86_64 AppImage to G:\C-Drive-Backup-PreReset\Installers\LibreLane.
# This stage does NOT install/run LibreLane, change Ubuntu packages, or edit RTL.
# Pinned official GitHub release 3.0.17, published 2026-10-26.
$ErrorActionPreference = 'Stop'
$Root = 'G:\C-Drive-Backup-PreReset'
$InstallDir = Join-Path $Root 'Installers\LibreLane'
$TempDir = Join-Path $Root 'Temp'
$Vhd = Join-Path $Root 'DevTools\WSL\Ubuntu-24.04\ext4.vhdx'
$Version = '3.0.17'
$AssetName = 'librelane-devshell-x86_64.AppImage'
$AssetSize = [int64]1398049312
$ExpectedSHA = 'c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c'
$Url = 'https://github.com/librelane/librelane/releases/download/3.0.17/librelane-devshell-x86_64.AppImage'
$File = Join-Path $InstallDir ('LibreLane-' + $Version + '-' + $AssetName)
$Part = $File + '.part'
$Log = $null

Write-Host '===== ASIC STAGE 2A: LIBRELANE VERIFIED DOWNLOAD ====='
if (-not (Test-Path -LiteralPath $TempDir -PathType Container)) {
    Write-Host 'FAIL | G: Temp directory missing; nothing downloaded'
    return
}
$Log = Join-Path $TempDir ('ASIC-Stage2A-LibreLane-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
function Report([string]$Level,[string]$Title,[string]$Message) {
    $line = "$Level | $Title | $Message"
    Write-Host $line
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
}

try {
    if (-not (Test-Path -LiteralPath $Vhd -PathType Leaf)) {
        throw "Expected G: WSL Ubuntu virtual disk missing: $Vhd"
    }
    Report PASS 'G: Ubuntu VHD' 'Present'
    $wsl = Join-Path $env:WINDIR 'System32\wsl.exe'
    $archResult = & $wsl -d Ubuntu-24.04 -u vaish -- uname -m 2>&1 | Out-String
    $archExit = $LASTEXITCODE
    $arch = ($archResult -replace '\x00','').Trim()
    if ($archExit -ne 0 -or $arch -ne 'x86_64') {
        throw "Expected Ubuntu x86_64 architecture; exit=$archExit; got=$arch"
    }
    Report PASS 'Ubuntu architecture' $arch

    $drive = Get-PSDrive -Name G
    $freeGB = [math]::Round(($drive.Free / 1GB), 1)
    if ($drive.Free -lt 12GB) {
        throw "G: free space $freeGB GB below guarded 12 GB minimum"
    }
    Report PASS 'G: available space' "$freeGB GB"

    $curl = Join-Path $env:WINDIR 'System32\curl.exe'
    if (-not (Test-Path -LiteralPath $curl -PathType Leaf)) {
        throw 'Windows curl.exe not found; no download attempted'
    }
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Report INFO 'Pinned publisher release' "LibreLane $Version ($AssetName)"
    Report INFO 'Expected size' "$AssetSize bytes"
    Report INFO 'Expected SHA256' $ExpectedSHA
    if (Test-Path -LiteralPath $Part -PathType Leaf) {
        throw "A prior partial file exists and was preserved: $Part. Inspect before retry."
    }
    if (Test-Path -LiteralPath $File -PathType Leaf) {
        Report INFO 'Existing package' 'Verifying without overwriting'
    } else {
        Report INFO 'Download destination' $File
        & $curl -fL --retry 3 --connect-timeout 25 --silent --show-error --output $Part $Url
        $downloadExit = $LASTEXITCODE
        if ($downloadExit -ne 0) {
            throw "Official GitHub download failed exit=$downloadExit; partial file preserved on G:"
        }
        $partSize = (Get-Item -LiteralPath $Part).Length
        if ($partSize -ne $AssetSize) {
            throw "Package size mismatch: got $partSize bytes expected $AssetSize; partial preserved"
        }
        $actualPartSha = (Get-FileHash -LiteralPath $Part -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualPartSha -ne $ExpectedSHA) {
            throw "SHA256 verification FAILED for partial file. Do not execute it. File preserved for inspection."
        }
        Move-Item -LiteralPath $Part -Destination $File -ErrorAction Stop
        Report PASS 'Download' 'Verified partial file promoted to final filename'
    }
    $actualSize = (Get-Item -LiteralPath $File).Length
    $actualSha = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSize -ne $AssetSize -or $actualSha -ne $ExpectedSHA) {
        throw "Final package verification FAILED (size=$actualSize SHA=$actualSha). Do NOT execute."
    }
    Report PASS 'Official asset size' "$actualSize bytes"
    Report PASS 'SHA256 integrity' $actualSha
    Report PASS 'Stored on G:' $File
    Report INFO 'Installation/execution' 'Not performed; next gate tests AppImage compatibility and LibreLane smoke'
} catch {
    Report FAIL 'Stage 2A verification' $_.Exception.Message
} finally {
    if ($Log) { Write-Host "INFO | Detailed log: $Log" }
    Write-Host '===== END ASIC STAGE 2A ====='
}

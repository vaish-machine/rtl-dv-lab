# ASIC Stage 0B — read-only diagnostics; only creates a G: Temp report.
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
if (!(Test-Path -LiteralPath $root -PathType Container)) {
    Write-Host 'FAIL | G: project root unavailable; no changes made'
    return
}
$dir = Join-Path $root 'Temp'
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$log = Join-Path $dir ('ASIC-WSL-Git-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$results = New-Object 'System.Collections.Generic.List[string]'
function Report([System.Collections.Generic.List[string]]$buffer,[string]$status,[string]$label,[string]$value) {
    $line = "$status | $label | $value"
    Write-Host $line
    [void]$buffer.Add($line)
}
Write-Host '===== ASIC STAGE 0B: WSL/GIT DIAGNOSIS ====='
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Report $results $(if($admin){'PASS'}else{'WARN'}) 'Administrator' $(if($admin){'yes'}else{'no; feature queries require elevation'})
$os = Get-CimInstance Win32_OperatingSystem
Report $results INFO 'Windows build' $os.Version
foreach($f in @('Microsoft-Windows-Subsystem-Linux','VirtualMachinePlatform')) {
    if($admin) {
        try {
            $state = (Get-WindowsOptionalFeature -Online -FeatureName $f -ErrorAction Stop).State
            Report $results $(if($state -eq 'Enabled'){'PASS'}else{'WARN'}) $f "$state"
        } catch { Report $results WARN $f $_.Exception.Message }
    } else {
        Report $results INFO $f 'not checked without elevation'
    }
}
try {
    $pkg = @(Get-AppxPackage -Name 'MicrosoftCorporationII.WindowsSubsystemForLinux')
    Report $results INFO 'WSL Store package' $(if($pkg.Count){($pkg | ForEach-Object { $_.Version }) -join ', '}else{'not installed for current user'})
} catch { Report $results WARN 'WSL Store package' $_.Exception.Message }
try {
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
    $names = @()
    if(Test-Path -LiteralPath $key) {
        $names = @(Get-ChildItem -LiteralPath $key | ForEach-Object { (Get-ItemProperty -LiteralPath $_.PSPath).DistributionName } | Where-Object { $_ })
    }
    Report $results INFO 'Registered Linux distros' $(if($names.Count){$names -join ', '}else{'none found in current user registry'})
} catch { Report $results WARN 'Linux distro registry' $_.Exception.Message }
foreach($svc in @('WslService','LxssManager','msiserver')) {
    $obj = Get-Service -Name $svc -ErrorAction SilentlyContinue
    Report $results INFO "Service $svc" $(if($obj){"$($obj.Status) (stopped can be normal)"}else{'not found'})
}
$git = Get-Command git.exe -ErrorAction SilentlyContinue
if($git) {
    Report $results PASS 'Git PATH' $git.Source
} else {
    Report $results WARN 'Git PATH' 'not found'
    $paths = @(
        (Join-Path $root 'DevTools\Git\cmd\git.exe'),
        (Join-Path $root 'Git\cmd\git.exe'),
        (Join-Path $env:ProgramFiles 'Git\cmd\git.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe')
    )
    $found = @($paths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
    Report $results $(if($found.Count){'PASS'}else{'WARN'}) 'Git common paths' $(if($found.Count){$found -join '; '}else{'not found'})
}
[void]$results.Add('Inspection only. WSL not updated, unregistered, repaired, or removed.')
$results | Out-File -LiteralPath $log -Encoding UTF8
Write-Host "INFO | Detailed log: $log"
Write-Host '===== END ASIC STAGE 0B ====='
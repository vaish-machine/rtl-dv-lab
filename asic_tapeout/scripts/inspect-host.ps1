# Stage 0 non-destructive host inspection. Only writes diagnostic log under G: Temp.
$ErrorActionPreference = 'Stop'
$root = 'G:\C-Drive-Backup-PreReset'
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    Write-Host 'FAIL | G: development root missing; no changes made'
    return
}
$logDir = Join-Path $root 'Temp'
New-Item -Path $logDir -ItemType Directory -Force | Out-Null
$log = Join-Path $logDir ('ASIC-Preflight-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$lines = New-Object System.Collections.Generic.List[string]
function Add-Check([System.Collections.Generic.List[string]]$buffer,[string]$status,[string]$name,[string]$value) {
    $line = "$status | $name | $value"
    Write-Host $line
    $buffer.Add($line)
}
Write-Host '===== ASIC STAGE 0 HOST PREFLIGHT ====='
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $ram = [math]::Round($os.TotalVisibleMemorySize / 1MB,1)
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='G:'"
    $free = if($disk) {[math]::Round($disk.FreeSpace / 1GB,1)} else {0}
    Add-Check $lines PASS 'Operating system' $os.Caption
    Add-Check $lines $(if($ram -ge 8){'PASS'}else{'WARN'}) 'RAM GB' "$ram (16 recommended)"
    Add-Check $lines $(if($free -ge 20){'PASS'}else{'WARN'}) 'G free GB' "$free (20 recommended minimum)"
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    Add-Check $lines INFO 'CPU' $cpu.Name
} catch {
    Add-Check $lines WARN 'Hardware scan' $_.Exception.Message
}
$git = Get-Command git.exe -ErrorAction SilentlyContinue
Add-Check $lines $(if($git){'PASS'}else{'WARN'}) 'Git' $(if($git){$git.Source}else{'not found'})
$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if($wsl) {
    try {
        $info = (& wsl.exe --list --verbose 2>&1 | Out-String).Trim()
        $lines.Add('WSL detail: ' + $info)
        Add-Check $lines INFO 'WSL' 'Present; check distro/version in detailed log'
    } catch {
        Add-Check $lines WARN 'WSL query' $_.Exception.Message
    }
} else {
    Add-Check $lines WARN 'WSL' 'not found'
}
$docker = Get-Command docker.exe -ErrorAction SilentlyContinue
Add-Check $lines INFO 'Docker' $(if($docker){'executable present (optional)'}else{'not found (optional with AppImage)'})
$lines.Add('No installation or repository source edits performed.')
$lines | Out-File -LiteralPath $log -Encoding utf8
Write-Host "INFO | Full log: $log"
Write-Host '===== END PREFLIGHT ====='
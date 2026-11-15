# Execution status — 2026-11-15

| Gate | Status |
|---|---|
| Existing repo baseline inspected and preserved | PASS |
| G0 Host/WSL2 inspection | PASS — Ubuntu 24.04 registered as WSL2 on G:; Linux user initialization pending; Git pending |
| G1 Freeze UART specification | PENDING |
| G2 Implement and verify RTL | PENDING |
| G3 Synthesis/SDC/pre-route STA | PENDING |
| G4 Floorplan/place/CTS/route | PENDING |
| G5 Post-route STA, DRC, LVS and review | PENDING |
| G6 Integrate official shuttle template and CI | PENDING |
| G7 Actual submission accepted | PENDING |
| G8 Real silicon arrived and validated | PENDING |

No EDA tools were installed, simulations executed, physical layouts produced or shuttles booked by this documentation-only commit.

**2026-11-15 actual Windows preflight (user-provided):** Windows 11 Home Single Language; RAM 15.9 GB; free G: 107.8 GB; Intel i7-9750H. Resources PASS. Git not found in PATH. WSL reports `Wsl/CallMsi/Install/REGDB_E_CLASSNOTREG`. Docker not found (optional). The WSL issue blocks the Linux ASIC toolchain; no repair has been attempted.

**Next action:** Enable the two missing WSL2 optional features with [Stage 0C](scripts/enable-wsl-features.ps1); reboot manually if requested, then inspect WSL. Do not unregister or remove any existing distro before backup.
**2026-11-15 Stage 0B detailed diagnosis (user-provided):** Windows 10.0.26300; admin yes; both `Microsoft-Windows-Subsystem-Linux` and `VirtualMachinePlatform` disabled; WSL Store package 3.0.3.0; no Linux distros in current user's registry; WslService/LxssManager not found; msiserver stopped (can be normal); Git not found in PATH/common install locations. **Next:** run [controlled Windows optional-feature enablement](scripts/enable-wsl-features.ps1), manually reboot if indicated, then verify WSL. Do not unregister/reset any distro. Git installation follows WSL recovery.

**2026-11-15 Stage 0C output (user-provided):** Microsoft-Windows-Subsystem-Linux already enabled PASS; VirtualMachinePlatform already enabled PASS; command reported no reboot needed. Because these features were disabled at Stage 0B, manually reboot and run [read-only Stage 0D WSL verification](scripts/check-wsl-runtime.ps1). Do not infer a functioning WSL runtime from feature state alone. Git remains pending.

**2026-11-15 Stage 0D (user-provided):** Both WSL optional features are Enabled, PASS. A generic Windows reboot-pending registry marker was detected; the original runtime script skipped WSL commands. WSL runtime remains UNVERIFIED. Next: perform a full Windows Restart, then rerun the updated read-only Stage 0D script. No OS/distro reset, Ubuntu install, Git installation, EDA installation, or WSL runtime validation is claimed.

**2026-11-15 Stage 0D after restart (user-provided):** both WSL Windows features Enabled (PASS); reboot-pending markers absent; all `wsl --version`, `wsl --status`, `wsl --list --verbose` still report `Wsl/CallMsi/Install/REGDB_E_CLASSNOTREG`. WSL application setup remains BROKEN; do not install an Ubuntu distro yet. Next: [Stage 0E guarded Microsoft-signed stable MSI WSL repair](scripts/repair-wsl-official-msi.ps1) (download to G:\C-Drive-Backup-PreReset\Installers\WSL; verified SHA256 and Authenticode; MSI verbose log in G: Temp). No uninstall/reset/unregister actions. Git remains missing. **Stage 0E has been documented but NOT executed on the user's PC.**

**2026-11-15 Stage 0E repair (user-provided):** WSL 3.0.5.0 x64 MSI downloaded to `G:\C-Drive-Backup-PreReset\Installers\WSL\wsl.3.0.5.0.x64.msi`; publisher SHA256 and Microsoft Authenticode signature both PASS; `msiexec` exit 0 (installation complete). Earlier WSL package 3.0.3.0 and missing native executable were observed **before the repair**. **Do not claim WSL is working yet.** Next: rerun read-only `scripts/check-wsl-runtime.ps1` to check `wsl --version`, `--status`, `--list --verbose`, and inspect results. Git installation remains PENDING. No Linux distribution was installed or reset.

**2026-11-15 Stage 0D runtime recheck (user-provided):** Windows WSL features both enabled; reboot pending: none; `wsl --version` successful, WSL 3.0.5.0 / kernel 6.18.58.1-1; `wsl --status` successful, default version 2. `wsl --list --verbose` reports **no distributions installed**, which is expected. WSL runtime is now VERIFIED. Next action: [Stage 0F guarded Ubuntu 24.04 installation to G:](scripts/install-ubuntu-gdrive.ps1), using Microsoft-supported `wsl --install --location` and the official online distro catalog. Install not yet executed; Git remains missing. No tapeout work beyond planning is claimed.

**2026-11-15 Stage 0F (user-provided):** G: free 119.5 GB PASS. Ubuntu installation script failed at its internal `Run-Wsl --version` preflight, reporting only "WSL version command did not succeed; do not install a distro." The script aborted **before** creating the Ubuntu install path or invoking `wsl --install`. This does not prove WSL has regressed; the last standalone Stage 0D WSL runtime test passed. Diagnose command capture and custom-location capability with the [Stage 0F read-only diagnostic](scripts/diagnose-stage0f.ps1) before attempting installation again. No Ubuntu installation, Git install, or EDA install has been verified.

**2026-11-15 Stage 0F diagnostic (user-provided):** Windows PowerShell 5.1, x64, `wsl.exe` exists, `wsl --version` returns exit=0 and WSL 3.0.5.0, destination G: Ubuntu directory absent, no registered distributions (expected `--list --verbose` exit -1), `wsl --install --help` returned exit=-1 without `--location`. This is **not** a valid capability check: Microsoft documents `wsl --help` as the canonical command. Corrected Stage 0F script now uses named string-array argument capture with exact exit/output diagnostics and the documented top-level help. Next: rerun **corrected** [Ubuntu G: installer](scripts/install-ubuntu-gdrive.ps1) and inspect compact results. Ubuntu installation has not yet been demonstrated.

**2026-11-15 Stage 0F rerun (user-provided): PASS.** Free G: space 119.5 GB; WSL 3.0.5.0 OK; custom `--location` available; no prior distros; Ubuntu-24.04 available in official catalog; WSL installer exit=0; distro registration PASS; WSL2 PASS; persisted `ext4.vhdx` located at `G:\C-Drive-Backup-PreReset\DevTools\WSL\Ubuntu-24.04\ext4.vhdx`. **Next:** first interactive Ubuntu launch and non-root account check with [Stage 0G](scripts/initialize-ubuntu-gdrive.ps1), from the same normal Windows user account. Then install Git inside WSL (Linux filesystem is on G:), check source control and choose RTL/EDA install path. No Ubuntu user/package installation or simulation evidence yet.

**2026-11-16 Stage 0G first-launch attempt (user-provided):** preflight failed at `wsl --list --quiet` with `Ubuntu-24.04 is not listed`, before Ubuntu launch or account creation. Stage 0F had already verified `wsl --list --verbose` with Ubuntu-24.04 registered as WSL2 and the G: VHDX. Likely PowerShell 5.1 UTF-16/NUL parsing issue with `--quiet`, but a Windows-account registration difference remains possible. Corrected [Stage 0G initializer](scripts/initialize-ubuntu-gdrive.ps1) now uses `--list --verbose`, strips NULs and prints exit code and compact listing; it refuses to launch if registration cannot be confirmed. No distro changes or Linux account creation were performed by the failed Stage 0G run. **Next:** run corrected script from same Windows account as Stage 0F, review results, avoid reinstalling or resetting Ubuntu.

**2026-11-16 Stage 0G live first-launch output (user-provided):** `wsl --list --verbose` returned exit=0, Ubuntu-24.04 `Stopped`, version 2. The distro's G: virtual disk exists. First-run provisioned a default non-root Unix account `vaish`; password setup reported success, and an interactive `vaish@Vaishakha:...$` Ubuntu shell appeared. **Stage 0G post-exit account/Ubuntu release checks have NOT run yet** because the user is still inside the interactive Linux shell. Next: type `exit` and inspect the PowerShell script's final account/OS PASS/FAIL results; do not count completion prematurely. Git and EDA installations remain pending.

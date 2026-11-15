# Execution status — 2026-11-15

| Gate | Status |
|---|---|
| Existing repo baseline inspected and preserved | PASS |
| G0 Host/WSL2 inspection | RESOURCE CHECK PASS; WSL 3.0.5 MSI repair succeeded; WSL runtime pending recheck; Git missing |
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

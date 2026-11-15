# Execution status — 2026-11-15

| Gate | Status |
|---|---|
| Existing repo baseline inspected and preserved | PASS |
| G0 Host/WSL2 inspection | RESOURCE CHECK PASS; both Windows features now Enabled; WSL runtime unverified; Git missing |
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

# Execution status — 2026-11-15

| Gate | Status |
|---|---|
| Existing repo baseline inspected and preserved | PASS |
| G0 Host/WSL2 inspection | BLOCKED: WSL error and Git missing from PATH |
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

**Next action:** Run [read-only WSL/Git check](scripts/diagnose-wsl-git.ps1) as administrator to inspect optional features, installed WSL app, registered distros and Git paths. Do not unregister or remove any existing distro before backup.
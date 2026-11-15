# Windows 11 + WSL2 + SKY130 toolchain

User storage policy: all development tools, installs, caches, source and logs under G:\C-Drive-Backup-PreReset where feasible; never use Downloads. Do not read PowerShell history. Inspect current code and logs only.

1. First run [scripts/inspect-host.ps1](scripts/inspect-host.ps1). It checks current machine state and writes one log under G:\C-Drive-Backup-PreReset\Temp; it DOES NOT install software or edit project source.
2. Review Windows 11 resources: 16 GB RAM recommended (8 GB minimum for LibreLane); enough G: disk capacity; check WSL2 Ubuntu availability.
3. Select WSL2 Ubuntu; if moving a distro to G: use official export/import processes rather than dragging a live virtual disk. Avoid large EDA builds on C:.
4. Start with LibreLane AppImage on WSL2, or supported Docker installation if needed. Verify a supported tiny example before introducing UART.
5. Record exact tool/PDK revisions. Use Yosys/OpenROAD/OpenSTA and applicable DRC/LVS tools via the selected flow. Consider ORFS separately for deeper floorplan and timing experiments.
6. Keep full build caches, WSL VHDX and generated PDK files outside Git. Add source/design configs, short reviewed reports and instructions into this repository.
7. The shuttle-specific technology, harness, area and IO requirements supersede generic SKY130 assumptions.

References:
- https://librelane.readthedocs.io/en/latest/installation/index.html
- https://librelane.readthedocs.io/en/stable/installation/appimage_installation/installation_win.html
- https://openroad-flow-scripts.readthedocs.io/en/latest/
- https://github.com/TinyTapeout/ttsky-verilog-template

AI may draft code, scripts, tests and design reviews. The engineer owns independent verification, signoff checks, exceptions, and factual resume claims.
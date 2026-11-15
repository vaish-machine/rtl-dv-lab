# Windows 11 + WSL2 + SKY130 toolchain

User storage policy: all development tools, installs, caches, source and logs under G:\C-Drive-Backup-PreReset where feasible; never use Downloads. Do not read PowerShell history. Inspect current code and logs only.

Linux project placement: Ubuntu 24.04 WSL2 is registered with its persistent ext4.vhdx on `G:\C-Drive-Backup-PreReset\DevTools\WSL\Ubuntu-24.04\ext4.vhdx`. For Linux simulator/EDA performance, keep the Linux source clone in `/home/vaish/projects/rtl-dv-lab` **inside** that G:-backed ext4 filesystem (not under `/mnt/c` or `/mnt/g`). Generated Linux packages and project data stay inside the G: VHDX. Short diagnostic logs can go directly to `/mnt/g/C-Drive-Backup-PreReset/Temp`. The Windows-side G: Projects folder remains for native Windows development and is not required for the WSL clone.

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
## Stage 0I — core RTL verification and synthesis baseline

After [Stage 0H Git setup](scripts/setup-git-wsl.sh) has passed, install Ubuntu 24.04 packaged `yosys`, `verilator`, `iverilog`, `build-essential`, `python3`, `python3-venv`, `python3-pip`, `tcl` and `z3` using the reviewed [Stage 0I install + smoke-test script](scripts/install-rtl-tools-wsl.sh). Ubuntu 24.04 package repositories provide these packages; the distro versions may be older than current upstream releases. Check and record actual versions rather than assuming current upstream. The script checks package availability, installs through apt, tests a standalone SystemVerilog counter with a self-checking Icarus testbench, lints the counter with Verilator, and synthesizes it in Yosys. Logs and small test files are kept under `G:\C-Drive-Backup-PreReset\Temp`; the original Git working tree is not modified.

The first counter smoke test is a **toolchain validation**, not evidence of UART verification or silicon implementation. The SKY130 PDK, OpenROAD/LibreLane physical flow, signoff tools, timing constraints and shuttle integration remain later distinct milestones.

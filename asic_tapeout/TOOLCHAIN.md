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

## Stage 2A — verified LibreLane AppImage download (prepared)

LibreLane's [official WSL2 installation guide](https://librelane.readthedocs.io/en/stable/installation/appimage_installation/installation_win.html) recommends the x86_64 development-shell AppImage and tests it with `librelane --smoke-test`. Rather than using a moving `latest` URL at execution time, Stage 2A pins the official GitHub `librelane/librelane` release **3.0.17** (published 2026-10-26). Official x86_64 asset: `librelane-devshell-x86_64.AppImage`; exact 1,398,049,312 bytes; SHA-256 `c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c` (publisher release metadata read 2026-11-16). Run [Stage 2A download script](scripts/download-librelane-gdrive.ps1) in normal Windows PowerShell. It checks x86_64 WSL, at least 12 GB free on G:, downloads to `G:\C-Drive-Backup-PreReset\Installers\LibreLane` with Windows curl, verifies byte count and SHA-256, and writes only a short report under G: Temp. It refuses to overwrite a file or reuse a `.part` file without inspection. **It does not install/extract/run anything.**

The follow-on Stage 2B will place the verified binary in Ubuntu native ext4 on the G:-backed virtual disk, then launch the devshell and execute LibreLane's official smoke test. LibreLane's packaged toolchain is distinct from Ubuntu apt-installed Yosys 0.33; always record each actual tool version. Do not claim any PDK-mapped netlist/GDS exists until a physical flow has been run and artifacts inspected. See [physical implementation plan](PHYSICAL_FLOW_PLAN.md).

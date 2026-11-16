# Exploratory UART 8N1 sky130A physical implementation — Stage 2C

**Status:** first real UART flow attempted on the user's workstation and **FAILED at Odb.CustomIOPlacement**; corrected pin-order config and preflight guard committed, rerun **PENDING**. This is a **digital macro/core**, not a fabricated chip or shuttle-integrated design.

## Source and configuration

- Top module: rtl/uart_core.sv, implemented using rtl/uart_tx.sv and rtl/uart_rx.sv.
- No RTL modifications for technology mapping. Simulation verified CLKS_PER_BIT 8/9/16/32; **physical RTL instance uses the current default 16**.
- Config: config.json; pin placement hints: pin_order.cfg. Stage 2C runner copies both files and all three RTL files to an isolated native-Linux working directory (G:-backed ext4) and records SHA256 hashes plus source commit.
- LibreLane: official pinned AppImage version 3.0.17; PDK family **sky130A**; standard cell library **sky130_fd_sc_hd**.
- Initial clock period: **100 ns**, equivalent to a provisional 10 MHz reference clock. With divider 16, the nominal UART rate is **625,000 baud**. This is a learning configuration, not a frozen product specification or evidence of actual timing closure.
- Initial core/die area: **250 µm × 250 µm** by explicit absolute floorplan. Deliberately generous for first flow; not an area-optimized result.
- CLK input: clk; synchronous active-low rst_n. All other parallel handshake/data/status ports are unpadded IP/core signals; only rx_i and tx_o are serial wires.
- Provisional pin order distributes TX input controls, RX output status/data and serial pins among four sides. Not an official shuttle pinout.

## Runner

Run scripts/run-uart-sky130-explore-wsl.sh as normal WSL user vaish. It guards a clean main Git checkout before fast-forwarding, verifies installed LibreLane AppImage SHA256 and G: space, stages files in a uniquely named native Ubuntu ext4 workspace, and invokes:

    librelane-devshell-x86_64.AppImage librelane --pdk-root ... --pdk sky130A --scl sky130_fd_sc_hd --flow Classic --jobs 2 --run-tag ... config.json

It treats nonzero LibreLane exit, timeout or missing/nonempty final GDS as a failure. It retains detailed source, intermediate logs, reports and any GDS under /home/vaish/DevTools/LibreLane/uart_sky130_explore in the existing G:-backed WSL2 virtual disk, and a compact run log under G:\C-Drive-Backup-PreReset\Temp. No files are added to Git and no Windows C: development folders are used.

## Review before any signoff or shuttle use

1. Validate actual run PDK revision, synthesis cell count/area, mapped netlist functionality, clock constraints, pre/post-route slack, setup/hold, slew/cap, and parasitic reports.
2. Review generated GDS and DEF, power/ground integration, placement/routing/pin access, DRC, LVS, and any waivers; a success marker alone does not prove full manufacturing signoff.
3. Consider timing corners, process/voltage/temperature, extracted parasitics, IO drive, ESD, power integrity and operating clock/baud tolerance.
4. G1 functional/shuttle specification remains not frozen; integrate into a provider-specific wrapper for actual tapeout. The UART core needs control/data handshakes that must be mapped to shuttle IO or a host interface. No shuttle slot or fabrication submission is represented.
5. Never describe an RTL-to-GDSII run as a foundry-certified signoff, an accepted tapeout or silicon validation.

Sources: official LibreLane 3.0.17 examples and configuration docs in librelane/librelane repository.

## Stage 2C first-run failure and correction (2026-11-16)

The first user-machine physical run reached the LibreLane Odb.CustomIOPlacement step, but stopped with `identifier/regex '#' requires a direction to be set first`. The first two lines of pin_order.cfg were ordinary `# ...` prose comments. LibreLane 3.0.17's `ioplace_parser.parse` treats only specific directives (`#N`, `#S`, `#E`, `#W`, optionally reversed `#NR` etc.) as control syntax; other `#` text becomes an invalid pin regex, and a regex before the initial side is an error. Removed the unsupported comment lines so the file begins with `#N`. The Stage 2C runner now validates the directives and checks every one of 24 top-level scalar port names (8 TX data bits and 8 RX data bits included) maps to exactly one pattern, before invoking LibreLane.

The first run reported non-fatal generic SDC fallback warnings: `PNR_SDC_FILE` and `SIGNOFF_SDC_FILE` were not specified. For this *exploration* they are acceptable only as a limitation; before any timing closure or signoff, provide reviewed, realistic clock, IO input/output delays, RX asynchronous treatment, reset assumptions, loads, and PDK corner constraints. The UART RTL files were unchanged by this fix. No full-flow or final GDSII PASS has been observed yet. Original run workspace `/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-UlhrMUrC` and diagnostics under G: Temp are preserved.

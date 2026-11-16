# Exploratory UART 8N1 sky130A physical implementation — Stage 2C

**Status:** corrected Stage 2C full exploratory UART physical flow **PASS** with verified final GDSII. Stage 2D read-only metrics extraction **PASS** (307 metrics), but route-DRC entries range 0–8 and generic fallback SDC remains; Stage 2E exact-key audit **PENDING**. This is a digital core, not fabricated silicon or a signed-off shuttle design.

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

## Stage 2C corrected rerun: first exploratory GDS created (2026-11-16)

Actual user-machine execution after the pin grammar fix **PASS**: four side directives and 24 scalar top-level UART pins mapped uniquely, LibreLane 3.0.17 Classic process exit zero, and nonempty `final/gds/uart_core.gds` output saved in `/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/`. GDS file **2,053,232 bytes**; SHA-256 **`3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3`**. Original stdout log `/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/librelane-explore-20261116-061728.log`; compact G: log `ASIC-Stage2C-UART-PHY-20261116-061723.log`. Git worktree clean; original 100 ns / 250 um square assumptions unchanged. This is **only exploratory GDS generation**, not a production or shuttle signoff.

Next: [Stage 2D independent GDS checksum and metrics audit](../../scripts/audit-uart-sky130-wsl.sh) will read the **existing run** and report timing, synthesis area, DRC/LVS, violations and power *if the flow produced corresponding metrics*. Missing metrics remain unverified; generic fallback SDC is not equivalent to a reviewed UART IO/CDC constraint set. Stage 2D has since executed; its results are summarized below.

## Stage 2D results — observed, not yet approved

User-confirmed read-only audit of the exact successful run: GDSII size and SHA256 PASS, source revision PASS, flow completion marker PASS, **307 final metrics keys** parsed. Reported Magic DRC errors **0** and LVS errors **0** (LVS net and device differences 0), but the route DRC metric family spans **0–8 across five entries**, so a final-stage DRC-clean conclusion is not justified yet. Setup/hold WNS, TNS and violation counts shown as zero under **generic fallback SDC**; this must not be cited as timing closure under final operating conditions. Area and cell count ranges aggregate several different metric keys and should not be interpreted as a final PPA point; quoted total power lacks verified units/conditions. Reports for post-route STA, Magic/KLayout DRC and Netgen LVS were present as step directories, which is not independent signoff. Full Stage 2D metrics saved by user under `G:\C-Drive-Backup-PreReset\Temp\ASIC-Stage2D-UART-Metrics-20261116-064301.json`.

[Stage 2E exact-key route DRC and physical report inspection](../../scripts/audit-uart-drc-details.py) completed on the user's WSL environment, identifying final route DRC=0 (intermediate iterations: 3, 0, 8, 0). It only reads the preserved physical run and writes detailed evidence to G: Temp; it does not modify the RTL, GDSII, reports or Git. Next decision depends on whether nonzero route DRC belongs to transient intermediate routing steps or the final routed design.

## Stage 2E result and Stage 2F provisional timing experiment

Stage 2E audit confirmed `route__drc_errors__iter:0=3`, `__iter:1=0`, `__iter:2=8`, `__iter:3=0`, and unqualified final `route__drc_errors=0`. This supports a clean final routing DRC metric after intermediate violations were resolved. Magic DRC 0, KLayout DRC 0 and LVS errors 0 in original saved metrics. These are reported metrics, not independent layout signoff. The remaining material timing issue is **generic fallback SDC** in Stage 2C: timing violation counts 0 do not establish final IO/clock performance.

Stage 2F (prepared, **not executed**) adds a separate, isolated physically constrained run using [provisional explicit 10 MHz SDC](constraints/uart_10mhz_provisional.sdc) and [guarded runner](../../scripts/run-uart-sky130-constrained-wsl.sh). Both implementation and signoff STA point to this same **experimental** SDC: 100 ns clock, provisional 0–10 ns synchronous input and output delays, 0.01 pF load, and explicit asynchronous `rx_i` input exception. These values are not a frozen external interface and must be replaced after clock, reset and wrapper requirements are known. The original Stage 2C GDS file remains untouched and its SHA-256 is checked both before and after the new flow.

# Tiny Tapeout SKY130 UART candidate — Stage 3A

**NOT a shuttle submission.** This staging area explores adapting the unchanged
UART RTL to the current official TinyTapeout/ttsky-verilog-template, inspected
on 2026-11-16 at commit a42e6662fab316e93b4e26399e21d41664a460b7.
The official template defines 8 dedicated inputs, 8 outputs, 8 bidirectional
pins plus clock, reset and enable. This candidate preserves the source UART.

## Candidate pin map

| TT port | Direction | UART signal |
|---|---|---|
| clk | input | clk |
| rst_n | input | synchronous active-low reset |
| ui_in[7:0] | input | tx_data[7:0] |
| uio_in[0] | input | tx_valid |
| uio_in[1] | input | rx_i, asynchronous; idle high |
| uo_out[7:0] | output | rx_data[7:0] |
| uio_out[2] | output | tx_ready |
| uio_out[3] | output | tx_o |
| uio_out[4] | output | rx_valid, one-cycle pulse |
| uio_out[5] | output | rx_framing_error, one-cycle pulse |
| uio_oe[7:0] | output-enable | fixed 0x3C; only 2..5 are outputs |
| uio_out[7:6] and [1:0] | output data | 0; bidirectional pin buffers disabled |
| ena | input | unused; official template describes as high when enabled |

Receive data and status are host-clock synchronous. Host must capture one-cycle
valid/error pulses. Transmit handshake requires tx_valid while tx_ready is high.
Parameter CLKS_PER_BIT=16; 10 MHz clock means nominal 625000 baud, but
actual shuttle clock/baud need to be selected and verified.

## Stage 3A deliverables

- Candidate wrapper: src/tt_um_vaish_uart.v
- Self-checking pin/TX/RX smoke test: test/tb_tt_um_vaish_uart.sv
- Guarded G:-backed WSL runner:
  ../../scripts/run-ttsky-uart-wrapper-smoke-wsl.sh

The script copies the original UART RTL and wrapper to a distinct native
Ubuntu ext4 workspace, then invokes Icarus and Yosys. It verifies the original
Stage 2C and 2F GDS hashes before and after. No GDS, PDK or RTL changes.
**PREPARED, NOT RUN** until user provides machine output.

## Required gates before real submission

1. **Tile footprint:** the exploratory standalone 250x250 um die is not
   a provider Tiny Tapeout tile. The official SKY template info.yaml lists
   supported tile shapes 1x1, 1x2, 2x2, 3x2, 4x2, 6x2, 8x2.
   The provider GDS workflow must confirm an actual suitable allocation.
2. **Shuttle & availability:** check https://www.tinytapeout.com/chips/.
   On 2026-11-16 the official page listed TTSKY26d/TTSKY26e
   closing 2026-11-30. Tile availability/cost have NOT been confirmed.
3. **Official template repository:** create a separate user-owned repository
   from TinyTapeout/ttsky-verilog-template; list all source files in
   info.yaml and test/Makefile. Do not submit rtl-dv-lab itself.
4. **CI & design validation:** pass official cocotb tests, RTL lint, GDS action,
   provider physical checks and selected tile-space verification. Do not
   substitute the standalone exploratory GDSII for the provider-generated one.
5. **Engineering signoff:** actual host clock/IO budgets, reset, async RX
   synchronizer and CDC/MTBF, PDK revision, timing, pad/ESD, power and output
   behavior remain to be reviewed against provider requirements.
6. **Explicit user action:** no allocation purchase, register/payment,
   shuttle submission or authorization has occurred.

Reference: https://www.tinytapeout.com/hdl/important/
Reference: https://github.com/TinyTapeout/ttsky-verilog-template


## Stage 3A result; Stage 3B official template dry-run
Stage 3A actual user-run (2026-11-16): Icarus/Yosys wrapper smoke PASS: I/O mask 0x3C, TX 0xA5, RX 0x5A, RX valid/error, original GDS SHA256s unchanged, Git clean.
**Stage 3B PREPARED, NOT RUN:** scripts/run-ttsky-template-integration-wsl.sh stages the pinned official SKY template (commit a42e6662fab316e93b4e26399e21d41664a460b7) in a separate G:-backed Ubuntu ext4 directory and overlays the unchanged UART RTL, TT wrapper, info.stage3b.yaml, test/Makefile source list and official test/tb.v top name. It checks the official harness compile with Icarus and structural hierarchy with Yosys, and runs local cocotb only if already installed (otherwise explicit SKIP). No provider GDS/CI or new user repository is created.
**IMPORTANT:** Metadata tiles: 1x1 is the unverified official-template placeholder, NOT a proven tile fit. The provisional 10MHz clock is not a finalized provider clock. Tile pricing, real IO/CDC/MTBF, physical fit, official CI, submission and purchase are OPEN.

## Stage 3B first run finding and corrected rerun

First local pinned official-template dry-run reached template integration but failed official `test/tb.v` Icarus compile because `tt_um_example` remained instantiated. A malformed Bash here-document in the Stage 3B *runner* had silently skipped Python patch execution and misreported overlay PASS. The corrected runner checks the Python patch completion marker and the exact testbench top before compiling. The failed workspace is preserved for auditing; corrected Stage 3B **RERUN PENDING**. This is not a UART RTL bug or a provider template GDS failure. No official CI run or purchase has occurred; tile 1x1 remains a placeholder.

**Stage 3B second local dry-run (2026-11-16):** Failed overlay validation after successful template checkout due to incorrect Python `Path`-object membership assertions on `tb` instead of source `text`. Fixed in `scripts/run-ttsky-template-integration-wsl.sh`, which now checks the modified official `test/tb.v` content and prints `template-check.log` diagnostics if anything fails. The prior run's directory `ttsky-Bd8KdlGI` is preserved. Corrected THIRD RUN pending. Neither original physical artifacts nor user RTL have been altered; tile size placeholder remains unverified.

## Stage 3B PASS; Stage 3C local cocotb prepared

Stage 3B corrected third user run (2026-11-16) PASS: official template checkout pinned to a42e6662fab316e93b4e26399e21d41664a460b7, source/metadata/testbench overlay, Icarus provider TB compilation, Yosys structural hierarchy; both standalone UART GDSII SHA256 values unchanged. The cocotb step was SKIPPED because not installed. Stage 3B successful workspace `/home/vaish/DevTools/LibreLane/ttsky_official_template_dryrun/ttsky-Lc4FY5ix` preserved.

Stage 3C local cocotb **PREPARED, NOT RUN**: `../../scripts/run-ttsky-local-cocotb-wsl.sh` creates a fresh G:-backed Ubuntu ext4 working copy of this successful template, checks the official commit and candidate source files, makes an isolated Python venv, downloads/installs the official template's cocotb==2.1.0 and pytest==8.4.2 dependencies within that venv, and runs `make clean`, `make` and `cocotb_tools.check_results`. No system-wide install, provider CI/GDS action or submission. 1x1 tile is UNVERIFIED placeholder; no tile purchase or timing/CDC signoff.

## Stage 3C passed; Stage 3D provider geometry screening prepared

2026-11-16 actual local WSL Stage 3C PASS: isolated venv on G:-backed native ext4 with cocotb 2.1.0/pytest 8.4.2; official template RTL Makefile and XML results checker succeeded, preserving both original UART GDSII hashes. Full run `ttsky_official_template_cocotb/run-i1DErq6p` on native G-backed Ubuntu ext4; no provider GitHub Actions were triggered.

Stage 3D [read-only pinned TT SKY geometry audit](../../scripts/audit-ttsky-tile-geometry-wsl.py) **PREPARED, NOT RUN**. Official provider `tt-support-tools` commit `9d13ff3e3e6202090740110438c6a10c1d62ca0f` lists 1x1 161.00x111.52um, 1x2 161.00x225.76um, 2x2 334.88x225.76um, 3x2 508.76x225.76um, etc. The standalone Stage2F reported instance area 53,897.9um² is larger than the 1x1/1x2 die rectangles; old cell area is **only** a screening proxy and NOT guaranteed comparable to a provider reimplementation. No tile size (including 2x2/3x2) is certified without the official provider GDS flow. No purchase, booking or submission; 1x1 overlay remains an unverified placeholder.

## Stage 3D confirmed geometry; Stage 3E 3x2 local physical trial prepared

Actual Stage3D user run (2026-11-16) PASS: official pinned TT SKY130 `tile_sizes.yaml` and DEF die-area geometry match for all seven supported template shapes; original Stage2C/2F GDS hashes and SDC hash unchanged; Stage3C cocotb XML had 1 testcase without failures/skips. Prior standalone Stage2F 53,897.9 µm² instance area is a **nontransferable screening proxy**, approximately 71.3% of the full 2x2 die and 46.9% of full 3x2 die (including routing/PDN and other unsupported deductions, real usable area is smaller). The default 1x1 remains an unproven placeholder.

Stage3E [guarded new local TT 3x2 footprint physical trial](../../scripts/run-ttsky-sky130-3x2-physical-trial-wsl.sh) **PREPARED, NOT RUN**. Makes new G:-backed workspace with successful official template and pinned official `tt-support-tools` checkout. It sets only the *copy's* info tile to 3x2, applies official 3x2 DEF and provider-style config recipe, uses pinned available LibreLane AppImage v3.0.17 Classic and existing G:-backed SKY130A PDK. This tests whether real provider-shape floorplan can be routed in an isolated experiment; it is NOT running Tiny Tapeout's actual GitHub GDS/precheck workflow or claiming 3x2 purchased/approved. The former 250×250 µm layouts remain immutable; outputs/logs stay on G:. Full DRC/LVS, timing/CDC, documented host clock, final provider configuration and shuttle acceptance remain OPEN.

**Stage 3E initial user attempt blocked before hardening (2026-11-16):** The overly strict `PDK_ROOT/sky130A` directory preflight failed. Original Stage2C/2F GDS SHA256, SDC SHA256 and LibreLane 3.0.17 AppImage SHA256 were verified unchanged. Corrected the Stage3E G:-backed runner to create/check a writable PDK root and delegate installed/cache PDK resolution to LibreLane, matching proven Stage2F flow behavior. This is not evidence that the RTL fails to fit 3x2; no 3x2 GDS was attempted. Corrected rerun PENDING; physical fit, official TT GDS CI/precheck and all signoff remain OPEN.

**Stage3E actual physical-flow attempt / Stage3F pending:** The G:-backed local TT 3x2 trial finally invoked LibreLane 3.0.17 with exact provider 3x2 DEF and original UART sources; process exited 0 after its final checker. It uses CIEL versioned SKY130A PDK rather than `PDK_ROOT/sky130A`. However the runner failed to find new GDS+metrics at the hardcoded template/runs path. Log reports LVS clear, max-slew warnings and unreported KLayout DRC; **3x2 physical fit and signoff are not verified**. [Read-only saved-output audit](../../scripts/audit-ttsky-3x2-physical-artifacts-wsl.py) Stage3F is PREPARED, NOT RUN: locate actual final results inside preserved `ttsky_sky130_3x2_trial/run-46NnPce8`, inspect relevant physical counters without re-running synthesis/route. Neither old GDS nor clock/SDC changed. No provider CI, tile purchase or shuttle submission.

## Stage 3F local physical GDS recovered, Stage 3G read-only check pending

User-run Stage3F (2026-11-16) PASS: the missing 3x2 local physical output actually exists under `template/src/runs/tt-3x2-20261116-123932/final/gds/tt_um_vaish_uart.gds`; SHA256 `4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599`, size 4,169,280 bytes. 305 final metrics keys; route DRC, Magic DRC, LVS, setup and hold violation counts each zero under experimental timing. However **22 aggregate max-slew violations** (11 nom_ss, 22 max_ss) and **missing KLayout DRC result** block signoff. Official TT template defaults `RUN_KLAYOUT_DRC=0`; active merge requires review. Reported 110874 µm² instance area over 114857.6576 µm² full die does NOT prove real placement utilization after excluding fillers. The local TT-footprint GDS is NOT provider-prechecked or submission-ready. Original Stage2C/2F GDS+SDC hashes preserved.

Stage3G [read-only slew/DRC/utilization audit](../../scripts/audit-ttsky-3x2-slew-and-drc-wsl.py) is PREPARED, NOT RUN. It checks exact pinned GDS hash and saved run configuration/reports and captures unresolved slew evidence and DRC configuration for repair planning. No PDK or layout changes, no provider Actions, payment or submission.

## Stage 3G actual PASS; Stage 3H saved slew endpoint extraction prepared

User-run Stage3G confirms **RUN_KLAYOUT_DRC=0 and RUN_KLAYOUT_XOR=0** in active local 3x2 config; no KLayout DRC report can be called PASS. Postroute local route DRC=0, Magic DRC=0, LVS=0, setup/hold counts=0, but **max-slew overall=22**, including slow-corner 22 max_ss /11 nom_ss counts. Genuine standard-cell density is **4.98%** (1,892 cells, 5,519.04µm²), rather than the physical-only/filler-inclusive 96.53% comparison. Smaller tiles not yet demonstrated and 3x2 neither production signoff nor provider accepted.

Stage3H **PREPARED, NOT RUN**: [non-destructive saved postroute OpenSTA endpoint extractor](../../scripts/audit-ttsky-3x2-postroute-slew-endpoints-wsl.py) reads specific checks.rpt in the preserved Stage3E run for two slow corners; locates actual violating pin names, slew limits, measured slews and negative slack where present. No new layout/EDA, PDK modification, provider CI or submission, and no speculative RTL change before the failing paths are known.

**Stage3I actual PASS, 2026-11-16:** All 22 max-SS postroute violating pins mapped to two nets, `net27` and `net16`, 11 each. Each net is associated with a clock-delay-buffer cell `sky130_fd_sc_hd__clkdlybuf4s25_1` (`fanout27/X` or `fanout16/X`); the reported 11 includes the driver output itself and does not mean 11 downstream loads. Topology suggests fanout/buffer transition concern, but top-level clock source, actual cell capacitances and repair method remain unproven. Worst observed `net27` 0.802130ns vs 0.750ns limit. KLayout DRC disabled and provider precheck/CDC/IO signoff OPEN.

**Stage3J PREPARED, NOT RUN:** [Static upstream clock buffer trace](../../scripts/audit-ttsky-3x2-slew-buffer-upstream-wsl.py) checks buffered nets' A/X connections and traces possible upstream drivers/clock alias inside the saved final mapped gate netlist only. It writes JSON/TXT under G: Temp, with no source, PDK, GDS, SDC or actual provider Action changes. Do not assume a clock-net repair is safe until trace confirms driver path.

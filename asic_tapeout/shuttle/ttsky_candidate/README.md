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

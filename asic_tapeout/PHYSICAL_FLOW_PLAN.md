# UART 8N1 — physical implementation preparation (Stage 2, not yet executed)

## Current evidence and scope

- User workstation: Windows 11, WSL2 Ubuntu 24.04.5 under G:-hosted ext4.vhdx, 16 GB-class RAM, existing Linux Git/Yosys/Verilator/Icarus/Z3.
- Stage 1A: UART self-checking directed simulations CPB 8/16, Verilator -Wall, generic Yosys synthesis PASS.
- Stage 1B: eight deterministic stress simulations PASS.
- Stage 1C: 12 monitored stress/async RX configurations PASS (revalidated as part of Stage 1D).
- Stage 1D: TX/RX reset matrix PASS for 80 bit-phase/configuration tuples.
- Stage 1E: four 32-step Yosys SMTBMC/Z3 safety checks PASS and TX handshake reachability PASS. These do not prove a whole UART frame or unbounded liveness.
- **No mapped SKY130 netlist, routed layout, STA, DRC, LVS, power signoff, shuttle acceptance or tested silicon yet.**

## Recommended next toolchain

Use official **LibreLane AppImage** on WSL2 for the initial open-source digital macro flow; LibreLane docs explicitly support WSL2/AppImage and provide `librelane --smoke-test` as an install check. The AppImage carries the intended toolchain; do not substitute Ubuntu Yosys 0.33 for LibreLane's packaged version in physical-flow results.

Official links:
- https://librelane.readthedocs.io/en/stable/installation/appimage_installation/installation_win.html
- https://librelane.readthedocs.io/en/stable/installation/appimage_installation/installation_linux.html
- https://github.com/librelane/librelane/releases/latest
- https://github.com/TinyTapeout/ttsky-verilog-template
- https://www.tinytapeout.com/hdl/templates/

### Pinned official artifact for Stage 2A

- Publisher: `librelane/librelane` on GitHub.
- Release: `3.0.17`, published **2026-10-26** (GitHub Releases metadata checked 2026-11-16).
- Asset: `librelane-devshell-x86_64.AppImage`.
- Size: **1,398,049,312 bytes**.
- Published SHA-256: `c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c`.
- Download URL: https://github.com/librelane/librelane/releases/download/3.0.17/librelane-devshell-x86_64.AppImage
- Script: [Stage 2A guarded G:-only download](scripts/download-librelane-gdrive.ps1). SHA-256 and exact byte size must match before running anything. Existing downloads are never overwritten. The script does not install, invoke, or extract AppImage.

### Planned Stage 2B

- Copy the **verified** binary from G: Installers into `/home/vaish/DevTools/LibreLane/` within native Linux ext4 (the distro virtual disk itself is stored on G:). Do not execute the binary directly under `/mnt/g` if mount semantics cause execution or performance issues.
- Make it executable, launch the documented LibreLane devshell, and run `librelane --smoke-test` with a local G:-backed Linux work directory.
- Record tool versions, PDK revision and the smoke test PASS/FAIL. PDK downloads, build outputs and caches stay on the G:-backed Linux filesystem; short summaries under G: Temp.
- After a known-good smoke test, create a *separate* UART macro configuration with a clock period and pin mapping explicitly labeled **exploratory**, not an approved shuttle signoff.

## Outstanding specification and shuttle integration gates

1. Freeze target **clock**, **UART baud**, tolerated divider/baud error, target reset source and output/interface requirements. The UART IP core has a parallel input handshake and one serial RX/TX pair; a shuttle top-level pin/host protocol must expose or translate those signals.
2. SKY130 is an initial candidate technology, not evidence of an open slot. Confirm current official shuttle, template, macro size, IO and submission rules before committing a final chip wrapper.
3. In the official Tiny Tapeout SKY130 project template, configure the required top-level IO and CI. A standalone UART core alone is **not** a Tiny Tapeout submission.
4. Perform PDK-specific synthesis, STA, floorplan, placement, CTS, routing, DRC and LVS; document limitations and any timing exceptions.
5. Distinguish a generated GDSII macro, a provider-accepted tapeout submission and physically received/tested silicon.

**No final IO pinout, clock value, source reset policy, PDK revision, area or PPA value is frozen by this planning document.**

## Executed setup milestones

- Stage 2A (user-provided 2026-11-16): **PASS**, release file and SHA256 verified, G: free 94.9 GB, no execution.
- Stage 2B (user-provided 2026-11-16): **PASS**. Official LibreLane 3.0.17 AppImage copied into native G:-backed Ubuntu ext4 with matching SHA256; Ubuntu uidmap installed; version and bundled smoke test passed, no AppArmor/sysctl modifications. This is environment validation only.

### Stage 2C (prepared, unexecuted)

- [Exploratory UART macro configuration](physical/uart_sky130_explore/README.md) and [guarded Classic runner](scripts/run-uart-sky130-explore-wsl.sh) staged in GitHub. Digital core uart_core default CPB=16, 100 ns provisional clock period (10 MHz nominal; 625000 UART baud), sky130A/sky130_fd_sc_hd, fixed *exploratory* 250 um x 250 um die area.
- Source RTL, config and pins staged into unique G:-backed Ubuntu ext4 work directory without altering original repo; full LibreLane reports/build outputs there, short summary in G: Temp. Runner invokes LibreLane Classic with two jobs and requires nonzero final GDS only if full command exits successfully.
- Next review: actual PDK revision, mapped cell statistics, STA setup/hold, DRC/LVS, final GDS/DEF/pinout and rule waivers, power/timing at multiple corners and shuttle-specific package. A successful experiment is not production signoff or tapeout.

### Stage 2C actual outcome / Stage 2D audit (2026-11-16)

- Corrected pin_order.cfg uses only LibreLane #N/#S/#E/#W side tokens, no unsupported prose-comment headers. User-reported G: workspace Stage 2C corrected rerun reached complete LibreLane Classic flow and generated a 2,053,232-byte uart_core.gds (sha256 `3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3`). This is first actual mapped/routed exploratory UART core output; no claim of signoff.
- Stage 2D [read-only saved run metrics audit](scripts/audit-uart-sky130-wsl.sh) prepared but **not run**. Checks exact GDS SHA256, original provenance and reported timing/area/DRC/LVS/power metrics; explicitly flags missing evidence, timing fallback SDC and nonzero violation counters. Read-only access to preserved physical workspace; audit files G: Temp.
- Before G3 closure, review exact STA setup/hold reports and environmental constraints; independently analyze layout rule and LVS evidence, PDK revision, synchronizer treatment/CDC, EQY and appropriate IO wrapper. An arbitrary 100 ns clock and 250 µm square die are learning parameters, not release requirements.

### Stage 2D physical evidence and Stage 2E focused review

Stage 2D exact-run audit on user Ubuntu passed authenticity/provenance and parsed 307 LibreLane final metrics. The saved metrics reported Magic DRC errors=0, LVS errors=0, and setup/hold violation counts=0; **route DRC errors aggregated to 0–8 over five stage-specific keys** (not yet categorized as final vs intermediate). Original flow used generic fallback implementation and signoff SDC; nominal 100ns clock is exploratory. Aggregated cell count range 0–14704 and area range 0–53897.9 represent several metric keys, not one final cell count or final cell area. Stage 2E [read-only per-key report audit](scripts/audit-uart-drc-details.py) **PENDING**; its output is required before deciding whether router corrections or just report classification is needed. No physical signoff, PDK/IO freeze or shuttle approval.

### Stage 2E resolution and Stage 2F provisional constrained experiment

Stage 2E read-only user-machine output on 2026-11-16 showed precise route DRC values: `route__drc_errors__iter:0=3`, iter1=0, iter2=8, iter3=0, and **final aggregate `route__drc_errors=0`**. Magic DRC=0, KLayout DRC=0, LVS errors=0 in saved metrics; no final DRC issue is proven by intermediate nonzero counters alone. Still no definitive signoff: original flow used generic fallback SDC, and the current wrapper/IO/clock constraints are not frozen.

Stage 2F adds an **experimental**, version-controlled [SDC](physical/uart_sky130_explore/constraints/uart_10mhz_provisional.sdc) with explicit 100 ns clock, nominal 0–10 ns input/output budgets, output load, uncertainty and asynchronous `rx_i` exception, plus [isolated constrained-run script](scripts/run-uart-sky130-constrained-wsl.sh). `SIGNOFF_SDC_FILE` and `PNR_SDC_FILE` both reference the same provisional constraints for experiment consistency; this is **not a signoff declaration**. Repeat full LibreLane Classic flow in a new G:-backed Ubuntu native ext4 workspace; verify the first successful GDS remains byte-identical. No Stage 2F execution/PASS exists yet. After Stage 2F, freeze actual board/shuttle clock, reset and IO interface and re-review STA/CDC, DRC/LVS/PPA and wrapper requirements.

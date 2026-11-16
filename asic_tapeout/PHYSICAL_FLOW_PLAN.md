# UART 8N1 — physical implementation milestones and remaining signoff gates

## Current evidence and scope

- User workstation: Windows 11, WSL2 Ubuntu 24.04.5 under G:-hosted ext4.vhdx, 16 GB-class RAM, existing Linux Git/Yosys/Verilator/Icarus/Z3.
- Stage 1A: UART self-checking directed simulations CPB 8/16, Verilator -Wall, generic Yosys synthesis PASS.
- Stage 1B: eight deterministic stress simulations PASS.
- Stage 1C: 12 monitored stress/async RX configurations PASS (revalidated as part of Stage 1D).
- Stage 1D: TX/RX reset matrix PASS for 80 bit-phase/configuration tuples.
- Stage 1E: four 32-step Yosys SMTBMC/Z3 safety checks PASS and TX handshake reachability PASS. These do not prove a whole UART frame or unbounded liveness.
- **Update:** Stage 2C and 2F subsequently generated routed SKY130 UART GDSII; Stage 2G compared those saved results. **No approved timing, CDC, full physical signoff, shuttle acceptance or tested silicon yet.**

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

### Stage 2F user results and Stage 2G next audit (2026-11-16)

Stage 2F constrained exploratory LibreLane Classic flow **PASS** in isolated G:-backed Ubuntu ext4. New GDS `uart_core.gds` 2,065,964 bytes SHA256 `d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af`. Reused unchanged RTL, PDK sky130A and `sky130_fd_sc_hd`, and added explicit but **provisional** 100 ns clock / 0–10 ns synchronous input-output delay / 0.01 pF load / asynchronous RX source exception for both PNR and signoff SDC. Saved final `route__drc_errors`, `magic__drc_error__count`, `klayout__drc_error__count`, `design__lvs_error__count`, `timing__setup_vio__count` and `timing__hold_vio__count` all reported **0**; WNS 0 must not be treated as positive timing margin. Instance count 14,722 (not a failure), reported instance/core area 53,897.9, power `5.6522698287153617e-05` with units/activity not reviewed. Original Stage 2C GDS SHA256 unchanged, source Git clean. No signed-off STA/CDC, no wrapper or tapeout.

Stage 2G [read-only comparison](scripts/audit-uart-sky130-sdc-compare.py) **PREPARED, NOT RUN**. It verifies hashes of both GDS files and source revision, checks actual resolved PNR/SIGNOFF_SDC_FILE paths and fallback warning absence, compares exact final metric keys and reports raw corner-specific entries without modifying the original or constrained run. Next post-audit work: freeze actual target clock and UART baud, reset/host handshake, IO constraints, synchronizer physical treatment, approved PDK/corners and shuttle top wrapper, then rerun verification/signoff with actual requirements.

### Stage 2G actual comparison and Stage 2H per-corner audit

Stage 2G user-provided output **PASS**: both GDS files matched known SHA256; original generic SDC fallback warning present, constrained run absent; its resolved PNR_SDC_FILE and SIGNOFF_SDC_FILE both point to the correct staged provisional SDC (SHA256 `a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4`); 307 metrics compared. Exact final Stage2C vs Stage2F metric values: routing DRC 0 vs 0, Magic DRC 0 vs 0, KLayout DRC 0 vs 0, LVS 0 vs 0, setup/hold violations 0 vs 0, unannotated nets **4 vs 3**, 14,704 vs 14,722 instances, equal reported instance/core area 53,897.9 and utilization 0.0865659 vs 0.0847552. WNS/TNS zero under provisional budgets are not positive margin. Power totals differ but are not comparable as physical power guarantees without supply units, switching activity, operating modes and corner checks. The user saved exact evidence under G: Temp, filename `ASIC-Stage2G-UART-Comparison-20261116-080554.json`.

Stage 2H [read-only post-PnR STA and net annotation audit](scripts/audit-uart-sta-annotation-wsl.py) **PREPARED, NOT RUN**. Uses LibreLane 3.0.17's known `checks.rpt` report structure and filtered unannotated metrics to identify residual driver names and whether the physically wired subset is affected; also surveys saved timing-path reports for `Startpoint`/`Endpoint` or `No paths found` evidence. Neither zero WNS nor generated GDS alone establishes timing coverage or final timing signoff. Actual clock, UART baud, IO budgets, reset policy, pad loads, PDK and accepted shuttle template all remain to freeze. All audit outputs remain on G:.

### Stage 2I evidence and Stage 2J timing-report classification

Stage 2I user audit confirmed 9/9 post-route PVT corners, each with 15 report files and 129 Startpoint plus 129 Endpoint mentions. One `No paths found` occurrence per corner is at line 72 of `checks.rpt`. The raw 3 unannotated drivers / physically filtered 0 metric persists. GDS/SDC hashes and original source commit remained verified. Reading LibreLane 3.0.17 `librelane/scripts/openroad/sta/corner.tcl` shows `checks.rpt` writes `report_checks -unconstrained` followed by `report_checks -slack_max -0.01`, then electrical violator checks. Thus the lone no-path phrase at the end of the second block most likely reflects **no negative-slack paths matching -0.01 ns threshold**, not absence of all timing paths. However, the earlier unconstrained report section can contain paths and must not be waived sight unseen.

Stage 2J [read-only `checks.rpt` report section audit](scripts/audit-uart-sta-coverage-sections-wsl.py) **PREPARED, NOT RUN**. It separates these two sections across nine corners, inspects `check_setup` evidence, reports true worst slack (`timing__setup__ws`/`timing__hold__ws` rather than zero-clipped WNS), and evaluates the saved propagated-clock state. The new script verifies preserved GDS and SDC hashes and writes evidence JSON/compact text exclusively under G: Temp. No rerouting, RTL changes or timing-waiver actions. Real IO clock/CDC and tapeout requirements still open.

### Stage 2J uncovered one path per corner; Stage 2K diagnostic

Stage 2J user-run inspection PASS for reading reports and verifying GDS/SDC hashes; 9/9 corners had no paths matching `report_checks -slack_max -0.01`, with actual worst setup slack between +84.252 and +88.056 ns and hold between +0.118 and +1.019 ns under provisional SDC. Crucially, **each unconstrained-path report had one Startpoint named `tx_valid (input port clocked by uart_clk)`**. The path Endpoint/Type and precise `check_setup` status have not yet been reviewed; cannot waive, identify as harmless or close timing signoff. Note that `tx_valid` already has provisional `set_input_delay` applied by the Stage 2F SDC. The remaining issue is timing path/endpoint coverage, not necessarily a missing input-delay statement.

Stage 2K [read-only exact path endpoint and check_setup audit](scripts/audit-uart-sta-unconstrained-endpoints-wsl.py) **PREPARED, NOT RUN**: prints per-corner startpoint+endpoint/path group and one representative saved unconstrained report excerpt with check_setup context, keeping all detailed evidence G:-only and the original RTL/GDS/SDC unchanged. A correct constraint change must follow actual endpoint evidence; final shuttle wrapper/CDC signoff remains open.


### Stage 2K: actual endpoint and async RX warning; Stage 2L report classification

Stage 2K original user-machine STA report inspection PASS: in every one of 9 PVT corners, report_checks -unconstrained outputs tx_valid (input port clocked by uart_clk) -> _390_ rising-edge flip-flop, Path Group uart_clk, Path Type max. The path source had applied **10 ns external input delay** and propagated clock network. check_setup warning is exactly "There is 1 input port missing set_input_delay" and names **rx_i**, which is intentionally the asynchronous serial input subject to set_false_path -from rx_i. Report command report_checks -slack_max -0.01 returned No paths found in all nine corners.

**Correcting the earlier Stage 2J interpretation:** OpenSTA documentation defines -unconstrained as reporting unconstrained paths **also**, not *only* unconstrained paths. A path appearing in this inclusive report is not proof it is unbounded. The warning identifies rx_i, not tx_valid. Do NOT add another tx_valid input delay, fabricate an asynchronous RX timing relationship or add an exception to silence warnings. Full timing-path required-time/slack evidence must be examined before constraint action.

Stage 2L [read-only real timing path classification](scripts/audit-uart-sta-real-coverage-wsl.py) **PREPARED, NOT RUN**: checks the original Stage 2C and Stage 2F GDS hashes, actual Stage 2F SDC hash, and saved OpenSTA report input external delay, numeric slack, required time and check_setup status across 9 PVT corners. It only writes G: Temp audit evidence, does not run LibreLane/STA again or alter existing files. Production signoff requires actual external clock/host budgets, CDC/MTBF signoff, power/ESD, PDK and shuttle top wrapper.

### Stage 2L parser issue and corrected read-only rerun (2026-11-16)

First user run of Stage 2L PASS for source/GDS/SDC SHA256 integrity, 9-corner saved-report extraction, `tx_valid` external delay and data required time, and attribution of check_setup's missing-input-delay warning to intentionally asynchronous `rx_i`. The audit's `slack=None` is not a measured timing result: the parser mistakenly expected `slack (MET) 84.2`, whereas OpenSTA formats the final numeric row as `84.2 slack (MET)`. The Stage 2L Python audit script has been corrected to accept numeric-before-slack `MET`/`VIOLATED` rows, validate built-in parsing fixtures, and expose raw slack candidates if unable to parse. **Corrected rerun pending**. Preserve Stage 2F SDC, GDS and reports; do not add fabricated RX delay or `tx_valid` false-path. Timing signoff remains pending actual clock/IO, CDC and shuttle requirements.


### Stage 2L corrected PASS; Stage 3A official SKY wrapper feasibility

Stage 2L user corrected read-only audit PASS across all 9 PVT STA corners: actual positive numeric tx_valid path slack MET, lowest +84.252296 ns (under provisional 100 ns, 0..10 ns external IO delays). The tx_valid source has applied external delay and required time in every corner. The missing input delay warning is async rx_i; no invented rx_i arrival time or extra tx_valid false-path needed. Both GDS hashes and provisional SDC SHA256 unchanged. This closes the earlier report-parser discrepancy, but not CDC/MTBF or real shuttle timing signoff.

Stage 3A UART candidate wrapper prepared **but not executed** under [shuttle/ttsky_candidate](shuttle/ttsky_candidate/README.md). Based on the checked official TinyTapeout SKY Verilog template interface: map TX byte to ui_in, RX byte to uo_out, bidirectional 0/1 as tx_valid/rx_i inputs and 2..5 as tx_ready/tx_o/rx_valid/rx_framing_error outputs (OE 0x3C). Unmodified UART RTL retained, CPB 16 provisional. A guarded WSL smoke will separately simulate wrapper TX/RX frames and run Yosys checks on staged copies. No real template repo or TT provider CI/GDS run yet. Prior standalone 250 x 250 um die does not imply TT tile fit. Official supported tile size must be selected by provider-driven sizing and user approval, and actual timing/IO requirements remain to be frozen.


### Stage 3A local simulation PASS; Stage 3B official SKY template dry-run
User-reported Stage 3A Icarus/Yosys wrapper test passed 2026-11-16 for TT bidirectional enable mask 0x3C, TX 8N1 0xA5, RX 8N1 0x5A, RX valid/framing and structural wrapper checks, preserving both original GDS SHA256 digests and clean Git.
Stage 3B **PREPARED, NOT RUN**: official TinyTapeout/ttsky-verilog-template main pinned to a42e6662fab316e93b4e26399e21d41664a460b7; fresh G:-backed Ubuntu ext4 copy, overlay four UART/wrapper sources, provisional info.yaml, test/Makefile and official TB top; local Icarus/Yosys verification, cocotb only if installed and otherwise SKIP. No real provider CI or GDS, no cost or tile fit verified, no submission. Provisional tiles: 1x1 is a template default only; actual minimum tile allocation remains OPEN, and so do true timing, PDK, CDC, power/pads, reset and signoff.

### Stage 3B failed local official template top rename; corrected runner

User-run first Stage 3B template dry-run reached official template checkout and source copy, but compile reported `Unknown module type: tt_um_example` at official `test/tb.v:31`. Root cause was malformed Bash heredoc around the Python patch in Stage 3B script, which bypassed intended `test/tb.v` top rename and returned a false overlay PASS. Corrected shell uses proper `if ! python3 <<'PY' ... PY then fail fi`, confirms the overlay marker and exact candidate `tt_um_vaish_uart user_project` instantiation, and keeps the original source, GDS, SDC and prior run workspace intact. Also corrected Stage 3A auxiliary static preflight for the same latent here-document issue; original Stage 3A actual Icarus/Yosys smoke checks passed independently. Corrected Stage 3B rerun PENDING. No provider GDS, tile fit or submission yet.

### Stage 3B second overlay validation fault (2026-11-16)

The second Stage 3B user-run passed official SKY template checkout and preserved the two standalone GDS SHA256 files, but stopped properly at Python official-template overlay validation. The embedded Python uses `tb` as a `pathlib.Path`; it incorrectly ran `"tt_um_vaish_uart user_project" in tb` rather than `... in text`, causing Python TypeError and preventing Icarus. The source-only patch fixes validation against the loaded and re-read official `test/tb.v`, adds compact overlay diagnostic log output and keeps the failed workspace untouched. An isolated four-source fixture passed the corrected metadata/Makefile/top assertions. **Third corrected Stage 3B run pending; no provider flow/signoff, tile-fit or submission.**

### Stage 3B actual PASS, Stage 3C pending cocotb run

The third user-machine Stage 3B local template dry-run PASS: official TinyTapeout/ttsky-verilog-template pinned commit a42e6662fab316e93b4e26399e21d41664a460b7, source YAML v6, Makefile, official test/tb.v overlay, Icarus compile and Yosys structural checks all succeed. Original two UART GDSII SHA256s unchanged. Existing cocotb check was explicitly SKIPPED because absent, not a PASS. Native G:-backed workspace `/home/vaish/DevTools/LibreLane/ttsky_official_template_dryrun/ttsky-Lc4FY5ix` preserved.

Stage 3C **PREPARED, NOT RUN**: the [local official-template RTL cocotb runner](scripts/run-ttsky-local-cocotb-wsl.sh) copies successful Stage 3B state into another isolated G:-backed Ubuntu ext4 directory, validates exact repo source/metadata and official commit, creates a local venv, installs only cocotb 2.1.0 and pytest 8.4.2 as pinned by the template into it with pip cache/temp on G:, runs local template test/Makefile and XML result checker, and preserves evidence. No apt/global Python, no provider GitHub GDS Actions or shuttle submission. Provider tile size 1x1 placeholder and experimental 10 MHz clock are not approved fit/spec. CDC/MTBF, real IO timing, full physical precheck and purchase/submission remain OPEN.

### Stage 3C actual cocotb pass and Stage 3D provider tile geometry preflight

The 2026-11-16 user-reported Stage 3C run **PASS** with official-template local cocotb 2.1.0 and pinned pytest 8.4.2, including XML results checker, using a separate G:-backed Ubuntu ext4 venv. Both original Stage2C/Stage2F GDS hashes unchanged. This is RTL test evidence, not a new TT-suitable GDSII or official CI acceptance.

Stage 3D [non-destructive official SKY tile geometry check](scripts/audit-ttsky-tile-geometry-wsl.py) **PREPARED, NOT RUN**. Fetches official provider `TinyTapeout/tt-support-tools` pinned commit `9d13ff3e3e6202090740110438c6a10c1d62ca0f` tile sizes and checks DEF die-area/pin template geometry for seven allowed shapes. Reference 1x1=161x111.52µm, 1x2=161x225.76µm; the earlier UART standalone 53,897.9 µm² reported instance area is above both rectangle areas. Comparing old place/route cell area to new provider tile capacity is a rough engineering benchmark **not signoff**: old filler cells and distinct synthesis/PDN, margins and wrapper impose different physical restrictions. 2x2 and 3x2 are only potential initial sizing trials, not proved fits. Real TT provider hardening/precheck is necessary before tile/cost selection or shuttle submission; these remain explicitly OPEN.

# Solo ASIC Tapeout — UART 8N1

**Status: UART STAGES 1A–1E PASS WITH EXPLICIT LIMITS; G1/G2 OPEN.** User workstation: Ubuntu 24.04 WSL2 stored on G:. Stage 1A directed simulation CPB 8/16, Verilator -Wall lint and generic Yosys synthesis PASS; Stage 1B 8/8 stress PASS; Stage 1C 12/12 monitored/async simulations revalidated; Stage 1D 4/4 reset-phase matrix PASS (80 phase tuples); Stage 1E 4/4 32-step bounded formal safety PASS plus TX handshake reachability cover PASS. These are user-provided test outputs, **not unbounded formal proof, CDC signoff, SKY130 mapping or physical layout**. Keep ../mux10_uvm_starter unchanged.

Goal: independently execute specification, RTL, independent verification, synthesis, SDC/STA, floorplanning, placement, CTS, routing, physical verification and a fabrication-shuttle submission, with AI-agent assistance.

Two separate deliverables:
- **RTL-to-GDSII:** reproduce and review a physically implemented SKY130 digital core, documenting checks and limitations.
- **Accepted tapeout:** port the verified core into an **official shuttle-specific template**, pass all provider checks, submit, and obtain acceptance evidence. A GDS file by itself is NOT a tapeout or full-chip signoff. Silicon delivery/validation is later.

Navigation:
- [45-day ROADMAP](ROADMAP.md)
- [UART SPEC](SPEC.md) (functional baseline candidate, final freeze still pending)
- [VERIFICATION_PLAN](VERIFICATION_PLAN.md)
- [TOOLCHAIN for Windows/WSL2](TOOLCHAIN.md)
- [SIGNOFF_CHECKLIST](SIGNOFF_CHECKLIST.md)
- [STATUS](STATUS.md)
- [Read-only host inspection script](scripts/inspect-host.ps1)

Candidate source: [rtl/uart_core.sv](rtl/uart_core.sv), [rtl/uart_tx.sv](rtl/uart_tx.sv), [rtl/uart_rx.sv](rtl/uart_rx.sv), [tb/tb_uart_core.sv](tb/tb_uart_core.sv). Run the guarded [Stage 1A UART regression](scripts/run-uart-baseline-wsl.sh) on the user's G:-backed Ubuntu WSL environment to establish actual UART simulation/lint/generic synthesis results. Spec G1 review and verification G2 remain open. Physical, shuttle and tool-generated outputs stay out of Git.

External references:
- https://librelane.readthedocs.io/en/latest/
- https://openroad-flow-scripts.readthedocs.io/en/latest/
- https://github.com/TinyTapeout/ttsky-verilog-template
- https://www.tinytapeout.com/guides/advanced-workshop/submit-your-design/

A separate GitHub repository based on the selected shuttle's official template **may be required for the actual submission**. This repository remains the canonical development source; link an immutable tagged source revision into the submission.
Initial directed regression: [Stage 1A script](scripts/run-uart-baseline-wsl.sh) (**PASS** on user workstation). Extended verification: [Stage 1B runner](scripts/run-uart-stress-wsl.sh) and [independent stress bench](tb/tb_uart_stress.sv) (**8/8 PASS on user workstation**). Stage 1C [assertion + async phase regression runner](scripts/run-uart-assertions-phase-wsl.sh) (**original 12/12 PASS; corrected checker requires revalidation**). Stage 1D [reset phase matrix and checker revalidation runner](scripts/run-uart-reset-matrix-wsl.sh) (**user-confirmed PASS**). Stage 1E [bounded formal runner](scripts/run-uart-formal-wsl.sh) (**4/4 safety and TX cover PASS in bounded scope**), with [initial CDC/reset architecture review](CDC_RESET_REVIEW.md) (**not signed off**). Next: [physical flow plan](PHYSICAL_FLOW_PLAN.md) and [Stage 2A pinned LibreLane download](scripts/download-librelane-gdrive.ps1) (**prepared, not executed**). See [STATUS](STATUS.md) for precise gates and evidence, and [VERIFICATION_PLAN](VERIFICATION_PLAN.md) for remaining work.

Environment progress: Stage 2A verified LibreLane AppImage download **PASS** and [Stage 2B official LibreLane devshell smoke test](scripts/install-smoke-librelane-wsl.sh) **PASS** (user-provided, bundled example only). Next: [Stage 2C first exploratory UART sky130A physical flow](scripts/run-uart-sky130-explore-wsl.sh), using [provisional config and pins](physical/uart_sky130_explore/README.md) (**prepared, NOT RUN**). No UART-specific mapped netlist, PPA/STA review or routed GDS yet.

Stage 2C corrected first full exploratory LibreLane Classic **PASS** and generated `uart_core.gds` in G:-backed Ubuntu (2,053,232 bytes, SHA256 `3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3`, user-reported 2026-11-16). **This is not physical signoff.** [Stage 2D read-only metrics/DRC/LVS/STA audit](scripts/audit-uart-sky130-wsl.sh) is **prepared, not run**. No official shuttle integration or silicon exists yet.

**Stage 2D user-run physical audit:** exact exploratory GDS hash and provenance PASS; 307 metric entries extracted, Magic DRC and LVS errors 0 in saved metrics, setup/hold counts 0 under generic fallback SDC; **routed DRC metrics span 0–8 across five keys**, so final routed DRC and timing signoff are **not** established. [Stage 2E focused read-only metric and report audit](scripts/audit-uart-drc-details.py) is **prepared, not yet run**, to print the exact route DRC keys and saved signoff report locations. All outputs remain on G:; no shuttle submission.

Stage 2E user-reported exact routing metrics confirmed **final route DRC=0** after intermediate iterations (3, 0, 8, 0); Magic DRC 0, KLayout DRC 0 and LVS errors 0. Explicit real-world timing IO/clock constraints still lack signoff. [Stage 2F provisional SDC flow](scripts/run-uart-sky130-constrained-wsl.sh) is **prepared, not run**: uses a separate G:-backed workspace and preserves the original generated GDSII. Its 10 MHz/10 ns IO-budget assumptions are for study, not a tapeout.

**Stage 2F user-run PASS (2026-11-16):** separate LibreLane Classic run with explicit **provisional** PNR and signoff SDC (100 ns UART core clock, 0–10 ns synchronous IO budgets, async RX source exception) generated a 2,065,964-byte UART GDSII (`d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af`). Saved final route/Magic/KLayout DRC, LVS, setup/hold violation metrics all 0. Original Stage 2C GDS hash unchanged; clean Git tree. Reported instance count 14,722 is expected, **not** a violation. Real wrapper/clock/CDC signoff OPEN. [Stage 2G read-only original-vs-constrained GDS, resolved SDC and metrics comparison](scripts/audit-uart-sky130-sdc-compare.py) **PREPARED, NOT RUN**.

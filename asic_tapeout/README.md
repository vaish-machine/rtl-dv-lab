# Solo ASIC Tapeout — UART 8N1

**Status: UART STAGES 1A AND 1B PASS; G2 VERIFICATION OPEN.** Ubuntu 24.04 WSL2 on G: is configured; UART Icarus directed simulation PASS (CPB 8/16), Verilator -Wall lint PASS, generic Yosys synthesis PASS, and 8/8 deterministic UART stress simulations PASS at CPB 8/9/16/32 × 2 seeds (user-provided results). Stage 1C revalidation and Stage 1D reset-phase matrix PASS on the user's PC (12 revalidated scenarios + four reset configurations, 80 phase tuples). Formal/CDCs and G2 closure remain open. Spec/shuttle freeze, SKY130 mapping and physical signoff remain pending. Preserve ../mux10_uvm_starter unchanged.

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
Initial directed regression: [Stage 1A script](scripts/run-uart-baseline-wsl.sh) (**PASS** on user workstation). Extended verification: [Stage 1B runner](scripts/run-uart-stress-wsl.sh) and [independent stress bench](tb/tb_uart_stress.sv) (**8/8 PASS on user workstation**). Stage 1C [assertion + async phase regression runner](scripts/run-uart-assertions-phase-wsl.sh) (**original 12/12 PASS; corrected checker requires revalidation**). Stage 1D [reset phase matrix and checker revalidation runner](scripts/run-uart-reset-matrix-wsl.sh) (**user-confirmed PASS**). Next Stage 1E [bounded formal runner](scripts/run-uart-formal-wsl.sh) (**not yet run**), with [initial CDC and reset architecture review](CDC_RESET_REVIEW.md). See [STATUS](STATUS.md) for precise gates and evidence, and [VERIFICATION_PLAN](VERIFICATION_PLAN.md) for remaining work.

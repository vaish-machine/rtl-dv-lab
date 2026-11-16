# Solo ASIC Tapeout — UART 8N1

**Status: ENVIRONMENT VERIFIED; UART DIRECTED SIMULATION PARTIAL PASS.** Stage 0I Icarus, Verilator and Yosys counter smoke checks PASS on Ubuntu 24.04 WSL2. Initial UART Icarus regressions PASS at CPB=8 and CPB=16; Verilator -Wall identified three timer-width warnings, now addressed in candidate RTL; lint rerun and UART Yosys synthesis still pending. Preserve ../mux10_uvm_starter unchanged.

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
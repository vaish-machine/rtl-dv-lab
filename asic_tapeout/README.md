# Solo ASIC Tapeout — UART 8N1

**Status: UART STAGE 1A PASS; COMPREHENSIVE VERIFICATION OPEN.** Ubuntu 24.04 WSL2 on G: is configured; UART Icarus directed simulation PASS at CPB=8 and CPB=16; Verilator -Wall lint PASS; generic Yosys synthesis PASS (all user-provided). Stage 1B extended deterministic UART stress testbench and runner are committed but NOT YET RUN. Specification/shuttle freeze, SKY130 mapping and physical signoff remain pending. Preserve ../mux10_uvm_starter unchanged.

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
Initial directed regression: [Stage 1A script](scripts/run-uart-baseline-wsl.sh) (**PASS** on user workstation). Extended verification: [Stage 1B runner](scripts/run-uart-stress-wsl.sh) and [independent stress bench](tb/tb_uart_stress.sv) (**pending first execution**). See [STATUS](STATUS.md) for precise gates and evidence, and [VERIFICATION_PLAN](VERIFICATION_PLAN.md) for remaining work.

# Solo ASIC Tapeout — UART 8N1

**Status: PLANNING.** Start from a small UART 8N1 TX/RX. Preserve ../mux10_uvm_starter unchanged.

Goal: independently execute specification, RTL, independent verification, synthesis, SDC/STA, floorplanning, placement, CTS, routing, physical verification and a fabrication-shuttle submission, with AI-agent assistance.

Two separate deliverables:
- **RTL-to-GDSII:** reproduce and review a physically implemented SKY130 digital core, documenting checks and limitations.
- **Accepted tapeout:** port the verified core into an **official shuttle-specific template**, pass all provider checks, submit, and obtain acceptance evidence. A GDS file by itself is NOT a tapeout or full-chip signoff. Silicon delivery/validation is later.

Navigation:
- [45-day ROADMAP](ROADMAP.md)
- [UART SPEC](SPEC.md) (draft; freeze before coding)
- [VERIFICATION_PLAN](VERIFICATION_PLAN.md)
- [TOOLCHAIN for Windows/WSL2](TOOLCHAIN.md)
- [SIGNOFF_CHECKLIST](SIGNOFF_CHECKLIST.md)
- [STATUS](STATUS.md)
- [Read-only host inspection script](scripts/inspect-host.ps1)

Project source to be added after spec approval: rtl/, tb/, physical/, shuttle/ and tools/. Keep generated files, large logs and PDK builds out of Git.

External references:
- https://librelane.readthedocs.io/en/latest/
- https://openroad-flow-scripts.readthedocs.io/en/latest/
- https://github.com/TinyTapeout/ttsky-verilog-template
- https://www.tinytapeout.com/guides/advanced-workshop/submit-your-design/

A separate GitHub repository based on the selected shuttle's official template **may be required for the actual submission**. This repository remains the canonical development source; link an immutable tagged source revision into the submission.
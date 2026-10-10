# rtl-dv-lab
💀 From Zero RTL to Billion-Dollar Silicon. No Shortcuts. Just Bugs, Hustle &amp; Billions. 🤑🔥
will create new silicon
# rtl-dv-lab

Practice repository for RTL design and verification using open-source simulation tools.

## Project progress

- **Counter**
  - Added counter RTL and a SystemVerilog testbench.
  - Simulated with Icarus Verilog; the observed count advanced from 1 through 4 before the test finished.
  - The counter changes were committed and pushed to GitHub earlier in the project.

- **Synchronous FIFO**
  - Added a FIFO specification, RTL, self-checking SystemVerilog testbench, and Makefile targets.
  - `make sim` passed at the default depth of 16 and at depth 5.
  - `make lint` passed with Verilator 5.032 and no warnings reported.

- **10-lane 2:1 mux**
  - Added a cocotb testbench using Icarus Verilog.
  - Directed truth-table and lane-selection tests plus 500 reproducible randomized vectors passed (`TESTS=1 PASS=1`).

- **3-input / 2-output router (starter)**
  - Prepared an example router and cocotb testbench for 8-bit ready/valid traffic.
  - Each input selects an output with a destination bit; each output uses round-robin arbitration and holds its selection under backpressure.
  - Router simulation has not yet been reported as run.

- **UVM mux testbench (starter)**
  - Prepared a class-based UVM example for the 10-lane mux.
  - It has not been run because VCS was not available in the WSL environment.

## Tools used

- Icarus Verilog 12.0 for simulation.
- cocotb 2.1.0 with Python 3.14 for Python-based verification.
- Verilator 5.032 for RTL linting.
- VCS was not installed; the UVM starter therefore remains unverified.

## Repository housekeeping

- Exclude generated simulation outputs such as `build/`, `sim_build/`, `results.xml`, and Python `.venv/` directories from Git.
- Accidental root-level files named `rtl\fifo.sv` and `verif\tb_fifo.sv` were identified; they match the proper files except for a trailing blank line. Keep `rtl/fifo.sv` and `verif/tb_fifo.sv` as the canonical paths and remove the backslash-named duplicates.
- The counter commit was pushed earlier. The later FIFO and verification files were shown staged, but a subsequent commit and push for those changes has not been confirmed.


# 10-lane mux UVM project

This repository is a standalone class-based UVM verification project for a combinational 10-lane, 2:1 mux. Its directory layout separates the DUT, interfaces, reusable verification environment, tests, and simulation output so the same structure can grow into block and SoC-level verification.

## Project history

Times are UTC for Git commit records and WSL local time when shown by terminal output. If a source conversation did not provide a reliable timestamp, the time is marked as not recorded rather than estimated.

- **2026-10-09 05:57 UTC** - Created the Git repository with an initial commit.
- **2026-10-09 10:02 UTC** - Added the first counter RTL module and testbench.
- **2026-10-09 17:27 UTC** - Added FIFO RTL and verification, plus a cocotb mux verification project.
- **2026-10-10 16:13 UTC** - Updated the repository README with project progress.
- **2026-10-19 16:35 WSL local time** - Downloaded and unpacked Accellera UVM 2020.3.2 under ~/eda/uvm-2020.3.2 and confirmed src/uvm_pkg.sv was present.
- **2026-10-19, time not recorded** - Set up mux10_uvm_starter to use Verilator 5.052 with UVM 2020.3.2. The initial build used high parallelism and took a long time compiling generated C++ code.
- **2026-10-20 00:41 UTC** - Added the Verilator UVM simulation flow to Git. Generated build files and compile/run logs are kept under sim/.
- **2026-10-20, time not recorded** - The Verilator build completed after the earlier long compile. A later UVM run reported scoreboard mismatches; the mux model was corrected to select each lane independently.
- **2026-10-21 09:31 WSL local time** - Organized the testbench with tb/interfaces/ and tb/tests/, and added UVM_INFO messages for test and sequence progress.
- **2026-10-21 09:51 WSL local time** - Cleaned the repository root so the UVM starter is the only project directory there, preserving Git metadata and the root .gitignore.
- **2026-10-21, time not recorded** - Confirmed FIFO simulations pass at depths 16 and 5. These simulations are separate from the UVM mux test.
- **2026-10-21, time not recorded** - Reorganized reusable UVM classes into separate files under tb/env/ and grouped them in mux10_env_pkg.sv.
- **2026-10-21, time not recorded** - Added rising-edge driver and monitor clocking blocks; the test waits one monitor cycle to capture the final driven item.

## Directory layout

- rtl/ - example mux DUT.
- tb/interfaces/ - SystemVerilog interfaces.
- tb/env/ - reusable UVM transaction, sequencer, sequences, driver, monitor, scoreboard, agent, and environment classes.
- tb/tests/ - UVM tests and test-specific configuration.
- sim/ - generated build files and compile/run logs.

Each reusable environment class is in its own .svh file under tb/env/. The package file tb/env/mux10_env_pkg.sv includes them in dependency order. This keeps the classes reusable while giving the simulator one package to compile.

## DUT assumptions

The example DUT has ten independent 2:1 mux lanes:

- Inputs: a[9:0], b[9:0], and sel[9:0].
- Output: y[9:0].
- Each lane computes y[i] = sel[i] ? b[i] : a[i].
- The DUT is combinational. The testbench clock only times stimulus and sampling. The driver clocking block drives inputs at the rising edge with output skew #0; the monitor clocking block samples pins with input skew #1step. The test waits an additional monitor edge after the last sequence item so the scoreboard receives the final transaction.

For a different DUT, update tb/tb_top.sv, tb/interfaces/mux_if.sv, and the relevant transaction and scoreboard classes under tb/env/.

## UVM components

- mux10_item: randomized input transaction and sampled output.
- mux10_sequencer: supplies transactions to the driver.
- mux10_driver: drives inputs through driver_cb on the rising clock edge.
- mux10_monitor: samples pins on the rising edge and publishes transactions.
- mux10_scoreboard: checks all ten mux outputs against the Boolean reference model.
- mux10_agent and mux10_env: assemble the active agent and scoreboard.
- mux10_directed_seq: applies all eight 1-bit truth-table combinations to every lane.
- mux10_random_seq: sends 200 randomized vectors.
- mux10_test: runs directed then random sequences and prints UVM_INFO progress messages.

## Compile and run with Verilator

The Makefile uses Verilator 5.052 or newer and UVM 2020.3.2. Set UVM_HOME if the UVM source directory is not at the default location:

    export UVM_HOME="$HOME/eda/uvm-2020.3.2/1800.2-2020.3.2/src"
    make sim

Run make sim from this directory. Generated files are placed under sim/build/; compiler output and UVM results are saved as sim/compile.log and sim/run.log. The class-based UVM testbench cannot run with Icarus Verilog.

# 10-lane mux UVM starter

This starter assumes the DUT is ten independent 2:1 muxes in parallel:

- `a[9:0]`, `b[9:0]`, and `sel[9:0]` are inputs.
- Each lane computes `y[i] = sel[i] ? b[i] : a[i]`.
- The DUT is combinational; the testbench clock is only used to time stimulus and sampling.

If your RTL has a different module name, port naming, bus width, or a shared select, update `tb/tb_top.sv` and the transaction/interface in `tb/mux10_pkg.sv` / `tb/mux_if.sv` accordingly. `rtl/mux10.sv` is only an example DUT; replace it with your RTL when integrating into the repo.

## UVM components

- `mux10_item`: randomized input transaction and sampled output.
- `mux10_sequencer`: supplies transactions to the driver.
- `mux10_driver`: drives inputs on the falling clock edge.
- `mux10_monitor`: samples pins on the rising edge and publishes transactions.
- `mux10_scoreboard`: checks all ten mux outputs against the Boolean reference model.
- `mux10_agent` and `mux10_env`: assemble the active agent and scoreboard.
- `mux10_directed_seq`: applies all eight 1-bit truth-table combinations to every lane.
- `mux10_random_seq`: sends 200 randomized vectors.
- `mux10_test`: runs directed then random sequences.

## Run with Synopsys VCS

The Makefile uses VCS's built-in UVM 1.2 library:

```sh
make sim
```

Or run the commands directly:

```sh
mkdir -p build/mux10_uvm
vcs -full64 -sverilog -ntb_opts uvm-1.2 -timescale=1ns/1ps \
  -f tb/filelist.f -top tb_top -o build/mux10_uvm/simv
./build/mux10_uvm/simv +UVM_TESTNAME=mux10_test
```

This standard class-based UVM testbench cannot run with Icarus Verilog. The previously reported Verilator 5.032 is too old for its newer, limited UVM support; use a UVM-capable VCS, Questa, or Xcelium installation, or upgrade Verilator and check its UVM limitations/version compatibility first. No simulator was available here to execute this UVM source, so validate it with your simulator after adapting the DUT port map.

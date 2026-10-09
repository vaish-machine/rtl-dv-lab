# 10-lane mux cocotb starter

This is an open-source alternative to the UVM starter. It uses Python/cocotb for verification and Icarus Verilog as the simulator.

Assumed DUT: ten independent combinational 2:1 mux lanes with 10-bit `a`, `b`, `sel`, and `y` buses, where `y[i] = sel[i] ? b[i] : a[i]`. `rtl/mux10.sv` is an example DUT; replace it or adapt `Makefile`'s source list and the test's signal names to match your RTL.

The test checks all eight truth-table combinations on every lane, selects each lane individually to catch lane mapping mistakes, then runs 500 deterministic pseudo-random vectors against a reference expression.

## Run in WSL

From this directory, install prerequisites if needed:

```sh
sudo apt update
sudo apt install -y make iverilog python3 python3-venv
```

Create an isolated Python environment, install cocotb, and run:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make SIM=icarus
```

The testbench is Python-based rather than UVM/SystemVerilog, but it exercises the same DUT and reference-model approach. The sample Makefile builds only the included example DUT; change `VERILOG_SOURCES`/`TOPLEVEL` and test signal names to connect your own module.

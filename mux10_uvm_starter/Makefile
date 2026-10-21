SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

VERILATOR ?= verilator
UVM_HOME ?= $(HOME)/eda/uvm-2020.3.2/1800.2-2020.3.2/src
SIM_DIR := sim
OBJ_DIR := $(SIM_DIR)/build/mux10_uvm

.PHONY: sim clean

sim:
	mkdir -p $(OBJ_DIR)
	$(VERILATOR) --binary --timing -j 2 -Wno-fatal \
	  --top-module tb_top --Mdir $(OBJ_DIR) \
	  +incdir+$(UVM_HOME) +incdir+tb/env +define+UVM_NO_DPI \
	  rtl/mux10.sv tb/interfaces/mux_if.sv \
	  $(UVM_HOME)/uvm_pkg.sv tb/env/mux10_env_pkg.sv tb/tests/mux10_test.sv tb/tb_top.sv \
	  2>&1 | tee $(SIM_DIR)/compile.log
	./$(OBJ_DIR)/Vtb_top +UVM_TESTNAME=mux10_test \
	  2>&1 | tee $(SIM_DIR)/run.log

clean:
	rm -rf $(SIM_DIR)/build $(SIM_DIR)/compile.log $(SIM_DIR)/run.log

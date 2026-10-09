IVERILOG ?= iverilog
VVP ?= vvp
VERILATOR ?= verilator

BUILD_DIR := build/fifo
RTL := rtl/fifo.sv
TB := verif/tb_fifo.sv

.PHONY: sim sim-default sim-odd lint clean

sim: sim-default sim-odd

sim-default:
	mkdir -p $(BUILD_DIR)
	$(IVERILOG) -g2012 -Wall -s tb_fifo -o $(BUILD_DIR)/tb_fifo.vvp $(RTL) $(TB)
	$(VVP) $(BUILD_DIR)/tb_fifo.vvp

sim-odd:
	mkdir -p $(BUILD_DIR)
	$(IVERILOG) -g2012 -Wall -s tb_fifo -Ptb_fifo.DEPTH=5 -o $(BUILD_DIR)/tb_fifo_depth5.vvp $(RTL) $(TB)
	$(VVP) $(BUILD_DIR)/tb_fifo_depth5.vvp

lint:
	$(VERILATOR) --lint-only -Wall --top-module fifo $(RTL)

clean:
	rm -rf $(BUILD_DIR)

VCS ?= vcs
SIMV := build/mux10_uvm/simv

.PHONY: sim clean

sim:
	mkdir -p build/mux10_uvm
	$(VCS) -full64 -sverilog -ntb_opts uvm-1.2 -timescale=1ns/1ps \
	  -f tb/filelist.f -top tb_top -o $(SIMV)
	./$(SIMV) +UVM_TESTNAME=mux10_test

clean:
	rm -rf build/mux10_uvm

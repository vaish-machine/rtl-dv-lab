package mux10_test_pkg;
    import uvm_pkg::*;
    import mux10_env_pkg::*;
    `include "uvm_macros.svh"

    class mux10_test extends uvm_test;
        `uvm_component_utils(mux10_test)
        mux10_env env;

        function new(string name, uvm_component parent);
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);
            env = mux10_env::type_id::create("env", this);
        endfunction

        task run_phase(uvm_phase phase);
            mux10_directed_seq directed_seq;
            mux10_random_seq random_seq;
            `uvm_info("MUX10_TEST", "Starting mux10_test", UVM_LOW)
            phase.raise_objection(this);
            directed_seq = mux10_directed_seq::type_id::create("directed_seq");
            random_seq = mux10_random_seq::type_id::create("random_seq");

            `uvm_info("MUX10_TEST", "Starting directed sequence (8 vectors)", UVM_LOW)
            directed_seq.start(env.agent.sequencer);
            `uvm_info("MUX10_TEST", "Directed sequence completed", UVM_LOW)

            `uvm_info("MUX10_TEST",
                      $sformatf("Starting random sequence (%0d items)", random_seq.num_items),
                      UVM_LOW)
            random_seq.start(env.agent.sequencer);
            `uvm_info("MUX10_TEST", "Random sequence completed", UVM_LOW)

            // Let the monitor sample the final item, driven on the prior edge.
            @(env.agent.monitor.vif.monitor_cb);
            #1step;
            `uvm_info("MUX10_TEST", "Final monitor sample captured", UVM_LOW)
            `uvm_info("MUX10_TEST", "All sequences completed; dropping objection", UVM_LOW)
            phase.drop_objection(this);
        endtask
    endclass

endpackage

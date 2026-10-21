class mux10_agent extends uvm_agent;
        `uvm_component_utils(mux10_agent)
        mux10_sequencer sequencer;
        mux10_driver driver;
        mux10_monitor monitor;

        function new(string name, uvm_component parent);
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);
            monitor = mux10_monitor::type_id::create("monitor", this);
            if (get_is_active() == UVM_ACTIVE) begin
                sequencer = mux10_sequencer::type_id::create("sequencer", this);
                driver = mux10_driver::type_id::create("driver", this);
            end
        endfunction

        function void connect_phase(uvm_phase phase);
            super.connect_phase(phase);
            if (get_is_active() == UVM_ACTIVE)
                driver.seq_item_port.connect(sequencer.seq_item_export);
        endfunction
    endclass

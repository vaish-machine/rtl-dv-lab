class mux10_sequencer extends uvm_sequencer #(mux10_item);
        `uvm_component_utils(mux10_sequencer)
        function new(string name, uvm_component parent);
            super.new(name, parent);
        endfunction
    endclass

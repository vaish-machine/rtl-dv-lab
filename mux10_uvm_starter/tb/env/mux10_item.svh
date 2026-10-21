class mux10_item extends uvm_sequence_item;
        rand bit [9:0] a;
        rand bit [9:0] b;
        rand bit [9:0] sel;
             bit [9:0] y;

        `uvm_object_utils_begin(mux10_item)
            `uvm_field_int(a, UVM_ALL_ON)
            `uvm_field_int(b, UVM_ALL_ON)
            `uvm_field_int(sel, UVM_ALL_ON)
            `uvm_field_int(y, UVM_ALL_ON)
        `uvm_object_utils_end

        function new(string name = "mux10_item");
            super.new(name);
        endfunction
    endclass

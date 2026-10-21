class mux10_driver extends uvm_driver #(mux10_item);
        `uvm_component_utils(mux10_driver)
        virtual mux_if vif;

        function new(string name, uvm_component parent);
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);
            if (!uvm_config_db#(virtual mux_if)::get(this, "", "vif", vif))
                `uvm_fatal("NOVIF", "mux_if virtual interface was not configured")
        endfunction

        task run_phase(uvm_phase phase);
            mux10_item req;
            forever begin
                seq_item_port.get_next_item(req);
                @(vif.driver_cb);
                vif.driver_cb.a   <= req.a;
                vif.driver_cb.b   <= req.b;
                vif.driver_cb.sel <= req.sel;
                seq_item_port.item_done();
            end
        endtask
    endclass

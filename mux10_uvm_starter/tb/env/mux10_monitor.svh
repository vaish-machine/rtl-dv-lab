class mux10_monitor extends uvm_component;
        `uvm_component_utils(mux10_monitor)
        virtual mux_if vif;
        uvm_analysis_port #(mux10_item) analysis_port;

        function new(string name, uvm_component parent);
            super.new(name, parent);
            analysis_port = new("analysis_port", this);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);
            if (!uvm_config_db#(virtual mux_if)::get(this, "", "vif", vif))
                `uvm_fatal("NOVIF", "mux_if virtual interface was not configured")
        endfunction

        task run_phase(uvm_phase phase);
            mux10_item observed;
            // The first rising edge is when the driver sends its first item.
            // Skip it because there is no completed input transaction to observe yet.
            @(vif.monitor_cb);
            forever begin
                @(vif.monitor_cb);
                observed = mux10_item::type_id::create("observed");
                observed.a   = vif.monitor_cb.a;
                observed.b   = vif.monitor_cb.b;
                observed.sel = vif.monitor_cb.sel;
                observed.y   = vif.monitor_cb.y;
                analysis_port.write(observed);
            end
        endtask
    endclass

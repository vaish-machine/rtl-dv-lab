package mux10_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

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

    class mux10_sequencer extends uvm_sequencer #(mux10_item);
        `uvm_component_utils(mux10_sequencer)
        function new(string name, uvm_component parent);
            super.new(name, parent);
        endfunction
    endclass

    class mux10_directed_seq extends uvm_sequence #(mux10_item);
        `uvm_object_utils(mux10_directed_seq)
        function new(string name = "mux10_directed_seq");
            super.new(name);
        endfunction

        virtual task body();
            mux10_item req;
            for (int combo = 0; combo < 8; combo++) begin
                req = mux10_item::type_id::create($sformatf("directed_%0d", combo));
                start_item(req);
                req.a   = {10{combo[0]}};
                req.b   = {10{combo[1]}};
                req.sel = {10{combo[2]}};
                finish_item(req);
            end
        endtask
    endclass

    class mux10_random_seq extends uvm_sequence #(mux10_item);
        `uvm_object_utils(mux10_random_seq)
        rand int unsigned num_items;

        function new(string name = "mux10_random_seq");
            super.new(name);
            num_items = 200;
        endfunction

        virtual task body();
            mux10_item req;
            repeat (num_items) begin
                req = mux10_item::type_id::create("random_item");
                start_item(req);
                if (!req.randomize())
                    `uvm_fatal("RANDFAIL", "Could not randomize mux10_item")
                finish_item(req);
            end
        endtask
    endclass

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
                @(negedge vif.clk);
                vif.a   <= req.a;
                vif.b   <= req.b;
                vif.sel <= req.sel;
                seq_item_port.item_done();
            end
        endtask
    endclass

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
            forever begin
                @(posedge vif.clk);
                observed = mux10_item::type_id::create("observed");
                observed.a   = vif.a;
                observed.b   = vif.b;
                observed.sel = vif.sel;
                observed.y   = vif.y;
                analysis_port.write(observed);
            end
        endtask
    endclass

    class mux10_scoreboard extends uvm_component;
        `uvm_component_utils(mux10_scoreboard)
        uvm_analysis_imp #(mux10_item, mux10_scoreboard) analysis_export;
        int unsigned checks;
        int unsigned errors;

        function new(string name, uvm_component parent);
            super.new(name, parent);
            analysis_export = new("analysis_export", this);
        endfunction

        function void write(mux10_item observed);
            bit [9:0] expected;
            expected = (observed.sel & observed.b) |
                       (~observed.sel & observed.a);
            checks++;
            if (observed.y !== expected) begin
                errors++;
                `uvm_error("MUX_MISMATCH",
                    $sformatf("a=%03h b=%03h sel=%03h y=%03h expected=%03h",
                              observed.a, observed.b, observed.sel,
                              observed.y, expected))
            end
        endfunction

        function void report_phase(uvm_phase phase);
            super.report_phase(phase);
            `uvm_info("MUX_CHECKS", $sformatf("checked=%0d errors=%0d", checks, errors), UVM_LOW)
            if (checks == 0)
                `uvm_error("NO_CHECKS", "Scoreboard received no transactions")
        endfunction
    endclass

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

    class mux10_env extends uvm_env;
        `uvm_component_utils(mux10_env)
        mux10_agent agent;
        mux10_scoreboard scoreboard;

        function new(string name, uvm_component parent);
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);
            agent = mux10_agent::type_id::create("agent", this);
            scoreboard = mux10_scoreboard::type_id::create("scoreboard", this);
        endfunction

        function void connect_phase(uvm_phase phase);
            super.connect_phase(phase);
            agent.monitor.analysis_port.connect(scoreboard.analysis_export);
        endfunction
    endclass

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
            phase.raise_objection(this);
            directed_seq = mux10_directed_seq::type_id::create("directed_seq");
            random_seq = mux10_random_seq::type_id::create("random_seq");
            directed_seq.start(env.agent.sequencer);
            random_seq.start(env.agent.sequencer);
            phase.drop_objection(this);
        endtask
    endclass
endpackage

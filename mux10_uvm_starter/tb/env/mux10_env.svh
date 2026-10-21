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

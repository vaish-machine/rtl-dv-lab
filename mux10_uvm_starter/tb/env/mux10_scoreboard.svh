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

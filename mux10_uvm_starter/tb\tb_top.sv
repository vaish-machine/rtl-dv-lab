`timescale 1ns/1ps

module tb_top;
    import uvm_pkg::*;
    import mux10_pkg::*;

    logic clk = 1'b0;
    always #5 clk = ~clk;

    mux_if mux_vif(clk);

    // Update this instance/port map to match your existing DUT.
    mux10 dut (
        .a   (mux_vif.a),
        .b   (mux_vif.b),
        .sel (mux_vif.sel),
        .y   (mux_vif.y)
    );

    initial begin
        uvm_config_db#(virtual mux_if)::set(null, "*", "vif", mux_vif);
        run_test("mux10_test");
    end
endmodule

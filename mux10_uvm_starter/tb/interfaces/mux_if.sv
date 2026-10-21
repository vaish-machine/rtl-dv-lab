interface mux_if(input logic clk);
    logic [9:0] a;
    logic [9:0] b;
    logic [9:0] sel;
    logic [9:0] y;

    // Inputs are driven at the rising edge; monitor sampling uses the prior
    // stable values immediately before the edge.
    clocking driver_cb @(posedge clk);
        default output #0;
        output a, b, sel;
    endclocking

    clocking monitor_cb @(posedge clk);
        default input #1step;
        input a, b, sel, y;
    endclocking
endinterface

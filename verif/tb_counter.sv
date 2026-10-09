module tb_counter;
    logic clk = 0;
    logic rst_n = 0;
    logic [3:0] count;

    counter dut (.clk(clk), .rst_n(rst_n), .count(count));

    always #5 clk = ~clk;

    initial begin
        repeat (2) @(posedge clk);
        @(negedge clk) rst_n = 1;

        repeat (4) begin
            @(posedge clk);
            @(negedge clk);
            if (count !== 4'(count)) begin
                $fatal(1, "Unexpected count value");
            end
            $display("count = %0d", count);
        end

        $display("Simulation finished");
        $finish;
    end
endmodule

// Stage 1E candidate: Yosys -formal / yosys-smtbmc bounded safety checks.
// Not synthesizable. The user provides no clock waveform; SMT time steps
// correspond to sampled rising-edge transitions in this single-clock design.
// External inputs are arbitrary per time step (anyseq).
// First sampled state forces rst_n low to initialize synchronous flops.
// No asynchronous metastability, setup/hold, coverage or physical guarantees.

module uart_tx_formal(input wire clk);
    parameter integer CLKS_PER_BIT = 8;
    (* anyseq *) reg rst_n;
    (* anyseq *) reg tx_valid;
    (* anyseq *) reg [7:0] tx_data;

    wire tx_ready, tx_o;
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) dut (
        .clk(clk), .rst_n(rst_n), .tx_valid(tx_valid), .tx_data(tx_data),
        .tx_ready(tx_ready), .tx_o(tx_o)
    );

    reg f_past_valid = 1'b0;
    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        if (!f_past_valid)
            assume(!rst_n);
        else begin
            // Synchronous reset must have made the transmitter idle
            // by the next sampled state.
            if (!$past(rst_n)) begin
                assert(tx_ready);
                assert(tx_o);
            end
            // Ready only represents the idle state; the line is high.
            if (rst_n && tx_ready)
                assert(tx_o);
            // An accepted byte causes start and busy state next cycle.
            if ($past(rst_n && tx_ready && tx_valid)) begin
                assert(!tx_ready);
                assert(!tx_o);
            end
        end
        if (rst_n && tx_ready && tx_valid)
            cover(1'b1);
    end
endmodule

module uart_rx_formal(input wire clk);
    parameter integer CLKS_PER_BIT = 8;
    (* anyseq *) reg rst_n;
    (* anyseq *) reg rx_i;

    wire [7:0] rx_data;
    wire rx_valid, rx_framing_error;
    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) dut (
        .clk(clk), .rst_n(rst_n), .rx_i(rx_i),
        .rx_data(rx_data), .rx_valid(rx_valid),
        .rx_framing_error(rx_framing_error)
    );

    reg f_past_valid = 1'b0;
    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        if (!f_past_valid)
            assume(!rst_n);
        else begin
            if (!$past(rst_n)) begin
                assert(!rx_valid);
                assert(!rx_framing_error);
                assert(rx_data == 8'd0);
            end
            if (rst_n) begin
                assert(!(rx_valid && rx_framing_error));
                if ($past(rst_n) && rx_data != $past(rx_data))
                    assert(rx_valid);
                if ($past(rst_n && rx_valid))
                    assert(!rx_valid);
                if ($past(rst_n && rx_framing_error))
                    assert(!rx_framing_error);
            end
        end
    end
endmodule

// Portable immediate-assertion-style UART black-box checkers for Icarus.
// These are simulation testbench modules, not synthesizable RTL, not formal SVA.
// All observations are at top-level pins after a fixed post-clock NBA delay.

module uart_tx_pin_checker #(
    parameter integer CPB = 16
) (
    input wire clk, rst_n,
    input wire tx_valid, tx_ready, tx_o,
    input wire [7:0] tx_data
);
    integer phase = -1; // -1 idle, 0 start, 1..8 data, 9 stop
    integer tick = 0;
    integer tx_accepted = 0;
    reg [7:0] accepted_byte = 8'd0;
    reg expected_bit;

    always @(posedge clk) begin
        if (!rst_n) begin
            phase = -1;
            tick = 0;
            #1;
            if (tx_o !== 1'b1 || tx_ready !== 1'b1)
                $fatal(1, "UART_ASSERT_FAIL: TX reset must be idle/high");
        end else begin
            if (phase == -1) begin
                if (tx_valid === 1'b1 && tx_ready === 1'b1) begin
                    accepted_byte = tx_data;
                    tx_accepted = tx_accepted + 1;
                    phase = 0;
                    tick = 0;
                end
            end else if (tick == CPB-1) begin
                tick = 0;
                phase = phase + 1;
                if (phase == 10)
                    phase = -1;
            end else begin
                tick = tick + 1;
            end
            #1;
            if (phase == -1) begin
                if (tx_o !== 1'b1 || tx_ready !== 1'b1)
                    $fatal(1, "UART_ASSERT_FAIL: TX idle waveform/ready");
            end else begin
                if (phase == 0)
                    expected_bit = 1'b0;
                else if (phase == 9)
                    expected_bit = 1'b1;
                else
                    expected_bit = accepted_byte[phase-1];
                if (tx_o !== expected_bit || tx_ready !== 1'b0)
                    $fatal(1, "UART_ASSERT_FAIL: TX waveform/ready phase=%0d tick=%0d got=%b expected=%b", phase, tick, tx_o, expected_bit);
            end
        end
    end
endmodule

module uart_rx_pin_checker (
    input wire clk, rst_n,
    input wire [7:0] rx_data,
    input wire rx_valid, rx_framing_error
);
    reg previous_valid = 1'b0;
    reg previous_error = 1'b0;
    reg [7:0] previous_data = 8'd0;
    reg has_sample = 1'b0;

    always @(posedge clk) begin
        #1;
        if (!rst_n) begin
            if (rx_valid !== 1'b0 || rx_framing_error !== 1'b0 || rx_data !== 8'd0)
                $fatal(1, "UART_ASSERT_FAIL: RX reset data/event");
            previous_valid = 1'b0;
            previous_error = 1'b0;
            previous_data = 8'd0;
            has_sample = 1'b0;
        end else begin
            if (rx_valid === 1'b1 && rx_framing_error === 1'b1)
                $fatal(1, "UART_ASSERT_FAIL: RX valid and framing error overlap");
            if (previous_valid && rx_valid)
                $fatal(1, "UART_ASSERT_FAIL: RX valid pulse exceeds one clock");
            if (previous_error && rx_framing_error)
                $fatal(1, "UART_ASSERT_FAIL: RX error pulse exceeds one clock");
            if (has_sample && rx_data !== previous_data && rx_valid !== 1'b1)
                $fatal(1, "UART_ASSERT_FAIL: RX data changed without valid event");
            previous_valid = rx_valid;
            previous_error = rx_framing_error;
            previous_data = rx_data;
            has_sample = 1'b1;
        end
    end
endmodule

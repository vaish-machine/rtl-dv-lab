// Independent waveform/scoreboard checks for initial UART RTL candidate.
// The testbench does not inspect any DUT FSM state or counters.
module tb_uart_core;
    parameter integer CPB = 16;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg rst_n = 1'b0;
    reg tx_valid = 1'b0;
    reg [7:0] tx_data = 8'h00;
    wire tx_ready, tx_o;
    wire [7:0] loop_data;
    wire loop_valid, loop_framing_error;

    // Real full-duplex wrapper; loop TX output back to RX input.
    uart_core #(.CLKS_PER_BIT(CPB)) dut (
        .clk(clk), .rst_n(rst_n),
        .tx_valid(tx_valid), .tx_data(tx_data),
        .tx_ready(tx_ready), .tx_o(tx_o),
        .rx_i(tx_o), .rx_data(loop_data),
        .rx_valid(loop_valid), .rx_framing_error(loop_framing_error)
    );

    // Independent serial stimulus to separately verify the receiver.
    reg rx_stimulus = 1'b1;
    wire [7:0] direct_data;
    wire direct_valid, direct_framing_error;
    uart_rx #(.CLKS_PER_BIT(CPB)) direct_rx (
        .clk(clk), .rst_n(rst_n), .rx_i(rx_stimulus),
        .rx_data(direct_data), .rx_valid(direct_valid),
        .rx_framing_error(direct_framing_error)
    );

    integer loop_count = 0;
    integer direct_count = 0;
    integer direct_error_count = 0;
    reg [7:0] last_loop_data = 8'h00;
    reg [7:0] last_direct_data = 8'h00;

    task automatic check(input bit condition, input [8*110-1:0] what);
        begin
            if (!condition) begin
                $display("UART_TEST_FAIL: %0s @ %0t", what, $time);
                $fatal(1);
            end
        end
    endtask

    // Observe registered pulses after nonblocking assignments settle.
    always @(posedge clk) begin
        #1;
        if (rst_n) begin
            if (loop_valid) begin
                loop_count = loop_count + 1;
                last_loop_data = loop_data;
            end
            if (loop_framing_error)
                $fatal(1, "Unexpected loopback framing error");
            if (direct_valid) begin
                direct_count = direct_count + 1;
                last_direct_data = direct_data;
            end
            if (direct_framing_error)
                direct_error_count = direct_error_count + 1;
            if (direct_valid && direct_framing_error)
                $fatal(1, "RX valid and framing error simultaneously asserted");
        end
    end

    task automatic send_and_verify_tx(input [7:0] byte_value, input bit attempt_busy);
        integer tick, bit_number;
        integer previous_count;
        begin
            previous_count = loop_count;
            @(negedge clk);
            while (!tx_ready)
                @(negedge clk);
            tx_data = byte_value;
            tx_valid = 1'b1;
            @(posedge clk); #2;
            check(tx_o === 1'b0, "TX start bit did not begin on accepted request");
            check(tx_ready === 1'b0, "TX remained ready while transmitting");
            @(negedge clk);
            tx_valid = 1'b0;
            for (tick = 1; tick < CPB; tick = tick + 1) begin
                @(posedge clk); #2;
                check(tx_o === 1'b0, "TX start duration incorrect");
            end
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                for (tick = 0; tick < CPB; tick = tick + 1) begin
                    @(posedge clk); #2;
                    check(tx_o === byte_value[bit_number], "TX data bit/order/timing wrong");
                    check(tx_ready === 1'b0, "TX ready asserted during data bits");
                    if (attempt_busy && bit_number == 3 && tick == 2) begin
                        @(negedge clk);
                        tx_data = ~byte_value; // must not corrupt active byte
                        tx_valid = 1'b1;       // busy request must not be accepted
                    end
                    if (attempt_busy && bit_number == 3 && tick == 5) begin
                        @(negedge clk);
                        tx_valid = 1'b0;
                    end
                end
            end
            for (tick = 0; tick < CPB; tick = tick + 1) begin
                @(posedge clk); #2;
                check(tx_o === 1'b1, "TX stop bit duration incorrect");
                check(tx_ready === 1'b0, "TX ready asserted before stop ended");
            end
            @(posedge clk); #2;
            check(tx_ready === 1'b1, "TX did not return to idle after stop");
            check(tx_o === 1'b1, "TX idle must be high");
            check(loop_count == previous_count + 1, "Loopback receiver did not produce one byte");
            check(last_loop_data == byte_value, "Loopback received byte mismatched TX");
            repeat (3) @(posedge clk);
        end
    endtask

    // Real serial-wire driver with only a 1-clock pause between frames;
    // no DUT state/timer introspection.
    task automatic drive_direct_frame(input [7:0] byte_value, input bit good_stop);
        integer bit_number;
        begin
            @(negedge clk);
            rx_stimulus = 1'b0;
            repeat (CPB) @(negedge clk);
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                rx_stimulus = byte_value[bit_number];
                repeat (CPB) @(negedge clk);
            end
            rx_stimulus = good_stop ? 1'b1 : 1'b0;
            repeat (CPB) @(negedge clk);
            rx_stimulus = 1'b1;
        end
    endtask

    task automatic verify_direct_good(input [7:0] byte_value);
        integer before_valid, before_error;
        begin
            before_valid = direct_count;
            before_error = direct_error_count;
            drive_direct_frame(byte_value, 1'b1);
            repeat (3) @(posedge clk);
            check(direct_count == before_valid + 1, "Direct RX did not produce one valid byte");
            check(last_direct_data == byte_value, "Direct RX byte does not match serial stimulus");
            check(direct_error_count == before_error, "Unexpected RX framing error");
        end
    endtask

    initial begin : run_tests
        integer errors_before;
        integer direct_before;
        reg [7:0] saved_data;
        repeat (5) @(posedge clk);
        @(negedge clk); rst_n = 1'b1;
        repeat (5) @(posedge clk);

        check(tx_ready === 1'b1 && tx_o === 1'b1, "UART reset/idle incorrect");
        send_and_verify_tx(8'h00, 1'b0);
        send_and_verify_tx(8'hff, 1'b0);
        send_and_verify_tx(8'h55, 1'b0);
        send_and_verify_tx(8'haa, 1'b1);
        send_and_verify_tx(8'h01, 1'b0);
        send_and_verify_tx(8'h80, 1'b0);

        verify_direct_good(8'h00);
        verify_direct_good(8'hff);
        verify_direct_good(8'h55);
        verify_direct_good(8'haa);
        verify_direct_good(8'h80);

        // A start pulse shorter than half a bit must be rejected.
        direct_before = direct_count;
        errors_before = direct_error_count;
        @(negedge clk); rx_stimulus = 1'b0;
        repeat (2) @(negedge clk);
        rx_stimulus = 1'b1;
        repeat (2 * CPB) @(posedge clk);
        check(direct_count == direct_before, "Glitch unexpectedly created data");
        check(direct_error_count == errors_before, "Glitch unexpectedly created framing error");

        // Bad stop must not replace the last valid byte.
        saved_data = direct_data;
        direct_before = direct_count;
        errors_before = direct_error_count;
        drive_direct_frame(8'hc3, 1'b0);
        repeat (2 * CPB) @(posedge clk);
        check(direct_count == direct_before, "Invalid stop was accepted");
        check(direct_error_count == errors_before + 1, "Framing error pulse missing/duplicated");
        check(direct_data == saved_data, "Invalid stop changed RX byte");

        // Recovery from a malformed frame.
        verify_direct_good(8'h96);

        // Start a TX byte and reset before completion. TX must return high.
        @(negedge clk);
        check(tx_ready === 1'b1, "TX unexpectedly busy before reset test");
        tx_data = 8'hf0;
        tx_valid = 1'b1;
        @(posedge clk); #2;
        check(tx_o === 1'b0, "Reset test transmission did not start");
        @(negedge clk); tx_valid = 1'b0;
        repeat (5) @(posedge clk);
        @(negedge clk); rst_n = 1'b0;
        @(posedge clk); #2;
        check(tx_o === 1'b1 && tx_ready === 1'b1, "Reset did not abort TX");
        check(loop_valid === 1'b0 && loop_framing_error === 1'b0 &&
              direct_valid === 1'b0 && direct_framing_error === 1'b0,
              "Reset did not clear RX pulses");
        repeat (3) @(posedge clk);
        @(negedge clk); rst_n = 1'b1;
        repeat (CPB * 2) @(posedge clk);
        check(tx_ready === 1'b1, "TX did not remain idle after reset");

        send_and_verify_tx(8'h3c, 1'b0);
        $display("UART_BASELINE_PASS: CPB=%0d loopback=%0d direct_rx=%0d framing_errors=%0d", CPB, loop_count, direct_count, direct_error_count);
        $finish;
    end

    initial begin
        #500000;
        $fatal(1, "UART testbench timed out");
    end
endmodule

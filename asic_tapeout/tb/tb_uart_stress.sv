// UART 8N1 extended RTL testbench (Stage 1B candidate).
// Tests interfaces only: never reads internal FSM states or timer registers.
// Deterministic LFSR payloads, continuous RX, stop errors, break and reset,
// and concurrent independent TX and RX transactions.
module tb_uart_stress;
    parameter integer CPB = 16;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg rst_n = 1'b0;
    reg tx_valid = 1'b0;
    reg [7:0] tx_data = 8'h00;
    wire tx_ready;
    wire tx_o;
    wire [7:0] loop_data;
    wire loop_valid;
    wire loop_error;

    uart_core #(.CLKS_PER_BIT(CPB)) core (
        .clk(clk), .rst_n(rst_n),
        .tx_valid(tx_valid), .tx_data(tx_data),
        .tx_ready(tx_ready), .tx_o(tx_o),
        .rx_i(tx_o), .rx_data(loop_data),
        .rx_valid(loop_valid), .rx_framing_error(loop_error)
    );

    reg rx_wire = 1'b1;
    wire [7:0] direct_data;
    wire direct_valid;
    wire direct_error;

    uart_rx #(.CLKS_PER_BIT(CPB)) independent_rx (
        .clk(clk), .rst_n(rst_n), .rx_i(rx_wire),
        .rx_data(direct_data), .rx_valid(direct_valid),
        .rx_framing_error(direct_error)
    );

    integer loop_count = 0;
    integer direct_count = 0;
    integer error_count = 0;
    reg [7:0] last_loop = 8'd0;
    reg [7:0] last_direct = 8'd0;
    integer seed = 20261116;

    function [31:0] next_lfsr(input [31:0] x);
        begin
            next_lfsr = {x[30:0], x[31] ^ x[21] ^ x[1] ^ x[0]};
        end
    endfunction

    task automatic check(input bit condition, input [8*120-1:0] message);
        begin
            if (!condition) begin
                $display("UART_STRESS_FAIL: %0s CPB=%0d time=%0t", message, CPB, $time);
                $fatal(1);
            end
        end
    endtask

    always @(posedge clk) begin
        #1; // Observe registered DUT signals after NBA update
        if (rst_n) begin
            if (loop_valid) begin
                loop_count = loop_count + 1;
                last_loop = loop_data;
            end
            if (direct_valid) begin
                direct_count = direct_count + 1;
                last_direct = direct_data;
            end
            if (direct_error)
                error_count = error_count + 1;
            if (loop_error)
                $fatal(1, "Loopback should never have a framing error");
            if (direct_error && direct_valid)
                $fatal(1, "Direct RX cannot be valid and framing error together");
        end
    end

    // Actively drive TX_VALID even while busy to verify transactions are ignored.
    task automatic send_tx(input [7:0] payload, input bit inject_busy);
        integer prev_count;
        begin
            prev_count = loop_count;
            @(negedge clk);
            while (tx_ready !== 1'b1)
                @(negedge clk);
            tx_data = payload;
            tx_valid = 1'b1;
            @(negedge clk);
            tx_valid = 1'b0;
            if (inject_busy) begin
                repeat (CPB * 3) @(negedge clk);
                check(tx_ready === 1'b0, "TX must be busy within data interval");
                tx_data = ~payload;
                tx_valid = 1'b1;
                repeat (2) @(negedge clk);
                tx_valid = 1'b0;
            end
            while (tx_ready !== 1'b1)
                @(negedge clk);
            repeat (4) @(negedge clk);
            check(loop_count == prev_count + 1, "TX loopback expected one received byte");
            check(last_loop == payload, "TX loopback payload mismatch");
        end
    endtask

    // Caller begins on a falling edge. Task ends on a falling edge so the
    // next raw_frame call starts immediately (zero idle clocks between frames).
    task automatic raw_frame(input [7:0] payload, input bit good_stop);
        integer bit_number;
        begin
            rx_wire = 1'b0;
            repeat (CPB) @(negedge clk);
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                rx_wire = payload[bit_number];
                repeat (CPB) @(negedge clk);
            end
            rx_wire = good_stop;
            repeat (CPB) @(negedge clk);
        end
    endtask

    task automatic send_direct(input [7:0] payload);
        integer before_count, before_error;
        begin
            before_count = direct_count;
            before_error = error_count;
            @(negedge clk);
            raw_frame(payload, 1'b1);
            rx_wire = 1'b1;
            repeat (CPB / 2 + 5) @(negedge clk);
            check(direct_count == before_count + 1, "Expected one independent RX byte");
            check(last_direct == payload, "Independent RX byte mismatch");
            check(error_count == before_error, "Unexpected direct RX framing error");
        end
    endtask

    task automatic send_bad_stop(input [7:0] payload);
        integer before_count, before_error;
        reg [7:0] saved;
        begin
            before_count = direct_count;
            before_error = error_count;
            saved = direct_data;
            @(negedge clk);
            raw_frame(payload, 1'b0);
            rx_wire = 1'b1;
            repeat (CPB + 5) @(negedge clk); // allow break recovery
            check(direct_count == before_count, "Bad stop accepted as valid byte");
            check(error_count == before_error + 1, "Bad stop must create exactly one error");
            check(direct_data == saved, "Bad stop must preserve last good byte");
        end
    endtask

    initial begin : regression
        reg [31:0] tx_rng;
        reg [31:0] rx_rng;
        reg [7:0] payload;
        integer i, before_count, before_error, before_loop;
        if ($value$plusargs("SEED=%d", seed)) begin end
        tx_rng = (32'h91e1_0da5 ^ seed);
        rx_rng = (32'h3ce7_5f21 ^ seed);
        repeat (5) @(negedge clk);
        rst_n = 1'b1;
        repeat (CPB) @(negedge clk);
        check(tx_ready === 1'b1 && tx_o === 1'b1, "Reset idle outputs incorrect");

        // Repeatable randomized TX bytes with occasional illegal busy requests.
        for (i = 0; i < 40; i = i + 1) begin
            tx_rng = next_lfsr(tx_rng);
            send_tx(tx_rng[7:0], (i % 4) == 0);
        end

        // Continuous back-to-back RX frames: no idle gap beyond each stop bit.
        @(negedge clk);
        for (i = 0; i < 50; i = i + 1) begin
            rx_rng = next_lfsr(rx_rng);
            before_count = direct_count;
            raw_frame(rx_rng[7:0], 1'b1);
            check(direct_count == before_count + 1, "Continuous RX dropped or duplicated a frame");
            check(last_direct == rx_rng[7:0], "Continuous RX payload mismatch");
        end
        rx_wire = 1'b1;
        repeat (CPB) @(negedge clk);

        // Short glitches are never full starts.
        before_count = direct_count;
        before_error = error_count;
        @(negedge clk);
        rx_wire = 1'b0;
        repeat (2) @(negedge clk);
        rx_wire = 1'b1;
        repeat (CPB * 2) @(negedge clk);
        check(direct_count == before_count && error_count == before_error,
              "Short start glitch produced an RX event");

        // Malformed stops and recovery must never clobber stored good data.
        send_bad_stop(8'h81);
        send_bad_stop(8'h00);
        send_bad_stop(8'hc3);
        send_direct(8'h96);

        // Sustained break should cause at most one stop error until idle returns.
        before_count = direct_count;
        before_error = error_count;
        @(negedge clk);
        rx_wire = 1'b0;
        repeat (CPB * 15) @(negedge clk);
        check(direct_count == before_count, "Break produced a valid frame");
        check(error_count == before_error + 1, "Break should produce one error");
        rx_wire = 1'b1;
        repeat (CPB + 5) @(negedge clk);
        send_direct(8'h5a);

        // Reset while an independent RX start/data transaction is in progress.
        before_count = direct_count;
        @(negedge clk);
        rx_wire = 1'b0;
        repeat (CPB + CPB / 2) @(negedge clk);
        rst_n = 1'b0;
        rx_wire = 1'b1;
        repeat (5) @(negedge clk);
        check(tx_o === 1'b1 && tx_ready === 1'b1, "Reset not reflected on TX");
        check(direct_valid === 1'b0 && direct_error === 1'b0, "Reset did not clear RX event");
        rst_n = 1'b1;
        repeat (CPB * 2) @(negedge clk);
        check(direct_count == before_count, "Aborted RX transaction generated data");
        send_direct(8'h42);

        // True independent TX/RX activity overlaps on two distinct input wires.
        before_loop = loop_count;
        before_count = direct_count;
        fork
            begin : tx_traffic
                integer n;
                reg [31:0] r;
                r = (32'h682d_43ad ^ seed);
                for (n = 0; n < 20; n = n + 1) begin
                    r = next_lfsr(r);
                    send_tx(r[7:0], (n % 5) == 0);
                end
            end
            begin : rx_traffic
                integer n;
                reg [31:0] r;
                integer expected_direct;
                r = (32'ha93e_40f3 ^ seed);
                @(negedge clk);
                for (n = 0; n < 20; n = n + 1) begin
                    r = next_lfsr(r);
                    expected_direct = direct_count;
                    raw_frame(r[7:0], 1'b1);
                    check(direct_count == expected_direct + 1, "Full-duplex RX dropped a frame");
                    check(last_direct == r[7:0], "Full-duplex RX byte mismatch");
                end
                rx_wire = 1'b1;
            end
        join
        check(loop_count == before_loop + 20, "Full-duplex TX count mismatch");
        check(direct_count == before_count + 20, "Full-duplex RX count mismatch");

        $display("UART_STRESS_PASS: CPB=%0d SEED=%0d loop=%0d direct=%0d frame_errors=%0d",
                 CPB, seed, loop_count, direct_count, error_count);
        $finish;
    end

    initial begin
        #10000000;
        $fatal(1, "UART extended regression timed out");
    end
endmodule

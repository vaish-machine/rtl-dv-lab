// Stage 1D: interface-only reset insertion in all 10 nominal 8N1 bit slots.
// Covers TX and independent RX start, 8 data bits and stop intervals.
// External checkers validate TX waveforms and RX event/data integrity.
// These are observed directed scenario bins, not full functional coverage.
`timescale 1ns/1ps
module tb_uart_reset_matrix;
    parameter integer CPB = 16;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg rst_n = 1'b0;
    reg tx_valid = 1'b0;
    reg [7:0] tx_data = 8'h00;
    wire tx_ready;
    wire tx_o;

    reg rx_wire = 1'b1;
    wire [7:0] rx_data;
    wire rx_valid;
    wire rx_error;

    uart_core #(.CLKS_PER_BIT(CPB)) dut (
        .clk(clk), .rst_n(rst_n),
        .tx_valid(tx_valid), .tx_data(tx_data),
        .tx_ready(tx_ready), .tx_o(tx_o),
        .rx_i(rx_wire), .rx_data(rx_data),
        .rx_valid(rx_valid), .rx_framing_error(rx_error)
    );

    uart_tx_pin_checker #(.CPB(CPB)) tx_checker (
        .clk(clk), .rst_n(rst_n),
        .tx_valid(tx_valid), .tx_ready(tx_ready),
        .tx_o(tx_o), .tx_data(tx_data)
    );

    uart_rx_pin_checker rx_checker (
        .clk(clk), .rst_n(rst_n),
        .rx_data(rx_data), .rx_valid(rx_valid),
        .rx_framing_error(rx_error)
    );

    integer tx_reset_hits[0:9];
    integer rx_reset_hits[0:9];
    integer valid_count = 0;
    integer error_count = 0;
    reg [7:0] last_rx = 8'd0;
    integer completed_tx = 0;
    integer recovered_rx = 0;

    task automatic check(input bit condition, input [8*120-1:0] message);
        begin
            if (!condition) begin
                $display("UART_RESET_FAIL: %0s CPB=%0d time=%0t", message, CPB, $time);
                $fatal(1);
            end
        end
    endtask

    always @(posedge clk) begin
        #2;
        if (rst_n) begin
            if (rx_valid) begin
                valid_count = valid_count + 1;
                last_rx = rx_data;
            end
            if (rx_error)
                error_count = error_count + 1;
        end
    end

    function automatic bit frame_level(input integer cycle_index, input [7:0] payload);
        integer slot_number;
        begin
            slot_number = cycle_index / CPB;
            if (slot_number == 0)
                frame_level = 1'b0;
            else if (slot_number <= 8)
                frame_level = payload[slot_number - 1];
            else
                frame_level = 1'b1;
        end
    endfunction

    task automatic send_good_tx(input [7:0] payload);
        integer watchdog;
        begin
            @(negedge clk);
            check(tx_ready === 1'b1, "TX not idle before recovery frame");
            tx_data = payload;
            tx_valid = 1'b1;
            @(negedge clk);
            tx_valid = 1'b0;
            watchdog = 0;
            while ((tx_ready !== 1'b1) && (watchdog < CPB*12)) begin
                @(negedge clk);
                watchdog = watchdog + 1;
            end
            check(tx_ready === 1'b1 && tx_o === 1'b1,
                  "TX recovery frame did not complete");
            repeat (2) @(negedge clk);
            completed_tx = completed_tx + 1;
        end
    endtask

    task automatic tx_abort_phase(input integer phase_number);
        integer elapsed;
        begin
            @(negedge clk);
            check(tx_ready === 1'b1, "TX must start idle");
            tx_data = 8'hac ^ phase_number;
            tx_valid = 1'b1;
            @(negedge clk);
            tx_valid = 1'b0;
            elapsed = phase_number * CPB + (CPB / 4);
            repeat (elapsed) @(negedge clk);
            check(tx_ready === 1'b0, "TX prematurely idle before phase reset");
            rst_n = 1'b0;
            @(posedge clk);
            #3;
            check(tx_o === 1'b1 && tx_ready === 1'b1,
                  "TX synchronous reset did not return idle/high");
            @(negedge clk);
            repeat (3) @(negedge clk);
            rst_n = 1'b1;
            repeat (CPB + 4) @(negedge clk);
            check(tx_ready === 1'b1 && tx_o === 1'b1,
                  "TX did not remain idle following reset");
            tx_reset_hits[phase_number] = tx_reset_hits[phase_number] + 1;
        end
    endtask

    task automatic send_good_rx(input [7:0] payload);
        integer bit_number, old_count, old_error;
        begin
            old_count = valid_count;
            old_error = error_count;
            @(negedge clk);
            rx_wire = 1'b0;
            repeat (CPB) @(negedge clk);
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                rx_wire = payload[bit_number];
                repeat (CPB) @(negedge clk);
            end
            rx_wire = 1'b1;
            repeat (CPB) @(negedge clk);
            repeat (CPB + 6) @(negedge clk);
            check(valid_count == old_count + 1,
                  "RX recovery frame did not produce exactly one valid event");
            check(error_count == old_error,
                  "RX recovery frame produced unexpected framing error");
            check(last_rx == payload, "RX recovery data mismatch");
            recovered_rx = recovered_rx + 1;
        end
    endtask

    task automatic rx_abort_phase(input integer phase_number);
        integer cycle_number, abort_after, old_count, old_error;
        reg [7:0] payload;
        begin
            old_count = valid_count;
            old_error = error_count;
            payload = (8'h59 ^ phase_number);
            abort_after = phase_number * CPB + (CPB / 4);
            @(negedge clk);
            for (cycle_number = 0; cycle_number <= abort_after;
                 cycle_number = cycle_number + 1) begin
                rx_wire = frame_level(cycle_number, payload);
                @(negedge clk);
            end
            // Synchronous reset interrupts the externally driven serial byte.
            rst_n = 1'b0;
            rx_wire = 1'b1;
            @(posedge clk);
            #3;
            check(rx_valid === 1'b0 && rx_error === 1'b0 && rx_data === 8'd0,
                  "RX synchronous reset did not clear event and stored byte");
            @(negedge clk);
            repeat (3) @(negedge clk);
            rst_n = 1'b1;
            repeat (CPB * 2 + 6) @(negedge clk);
            check(valid_count == old_count,
                  "RX aborted frame generated a valid event");
            check(error_count == old_error,
                  "RX aborted frame generated framing error after reset");
            rx_reset_hits[phase_number] = rx_reset_hits[phase_number] + 1;
        end
    endtask

    initial begin : run
        integer phase;
        for (phase = 0; phase < 10; phase = phase + 1) begin
            tx_reset_hits[phase] = 0;
            rx_reset_hits[phase] = 0;
        end
        repeat (6) @(negedge clk);
        rst_n = 1'b1;
        repeat (CPB * 2) @(negedge clk);
        check(tx_ready === 1'b1 && tx_o === 1'b1, "Initial TX idle wrong");

        // Reset at early point of each start/data/stop interval, followed by
        // a full normal TX transaction to prove recovery after each abort.
        for (phase = 0; phase < 10; phase = phase + 1) begin
            tx_abort_phase(phase);
            send_good_tx(8'h25 ^ phase);
        end

        // Independently reset RX at early point of each bit interval. Ensure
        // no partial frame emerges and next correctly framed byte is accepted.
        for (phase = 0; phase < 10; phase = phase + 1) begin
            rx_abort_phase(phase);
            send_good_rx(8'hd3 ^ phase);
        end

        for (phase = 0; phase < 10; phase = phase + 1) begin
            check(tx_reset_hits[phase] == 1, "TX reset scenario bin not hit");
            check(rx_reset_hits[phase] == 1, "RX reset scenario bin not hit");
        end
        check(completed_tx == 10, "TX recovery count incorrect");
        check(recovered_rx == 10 && valid_count == 10,
              "RX recovery count incorrect");
        check(error_count == 0, "Unexpected framing errors during reset matrix");
        check(tx_checker.tx_accepted == 20,
              "TX accepted handshake count incorrect: 10 aborted plus 10 recovered");
        $display("UART_RESET_PASS: CPB=%0d tx_reset_phases=10 rx_reset_phases=10 tx_recovered=10 rx_recovered=10",
                 CPB);
        $finish;
    end

    initial begin
        #10000000;
        $fatal(1, "UART reset-phase regression timed out");
    end
endmodule

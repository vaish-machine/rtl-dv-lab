// Stage 1C: asynchronous RX transitions and modest baud-offset tests.
// Uses real nanosecond wire delays, deliberately not aligned to clock edges.
// Check only externally visible RX data/event signals.
`timescale 1ns/1ps
module tb_uart_async_phase;
    parameter integer CPB = 16;

    reg clk = 1'b0;
    always #5 clk = ~clk; // 10 ns period
    reg rst_n = 1'b0;
    reg rx_wire = 1'b1;
    wire [7:0] rx_data;
    wire rx_valid;
    wire rx_error;
    integer valid_count = 0;
    integer error_count = 0;
    reg [7:0] last_received = 8'd0;

    uart_rx #(.CLKS_PER_BIT(CPB)) dut (
        .clk(clk), .rst_n(rst_n), .rx_i(rx_wire),
        .rx_data(rx_data), .rx_valid(rx_valid),
        .rx_framing_error(rx_error)
    );
    uart_rx_pin_checker monitor (
        .clk(clk), .rst_n(rst_n), .rx_data(rx_data),
        .rx_valid(rx_valid), .rx_framing_error(rx_error)
    );

    task automatic check(input bit condition, input [8*120-1:0] what);
        begin
            if (!condition) begin
                $display("UART_ASYNC_FAIL: %0s CPB=%0d t=%0t", what, CPB, $time);
                $fatal(1);
            end
        end
    endtask

    always @(posedge clk) begin
        #2; // sample after synchronous RX and checker updates
        if (rst_n) begin
            if (rx_valid) begin
                valid_count = valid_count + 1;
                last_received = rx_data;
            end
            if (rx_error)
                error_count = error_count + 1;
        end
    end

    // A bit cell lasts CPB*10+delta nanoseconds, modelling a slightly
    // different sender baud rate. Start is phase ns after a falling edge.
    task automatic drive_frame(input [7:0] payload,
                               input integer phase,
                               input integer delta,
                               input bit good_stop);
        integer bit_period_ns, i;
        begin
            bit_period_ns = CPB * 10 + delta;
            @(negedge clk);
            #(phase);
            rx_wire = 1'b0; // start
            #(bit_period_ns);
            for (i = 0; i < 8; i = i + 1) begin
                rx_wire = payload[i];
                #(bit_period_ns);
            end
            rx_wire = good_stop ? 1'b1 : 1'b0;
            #(bit_period_ns);
            rx_wire = 1'b1; // idle/recovery
        end
    endtask

    task automatic expect_frame(input [7:0] payload,
                                input integer phase,
                                input integer delta,
                                input bit good_stop);
        integer old_valid, old_error;
        reg [7:0] old_data;
        begin
            old_valid = valid_count;
            old_error = error_count;
            old_data = rx_data;
            drive_frame(payload, phase, delta, good_stop);
            repeat (CPB + 8) @(negedge clk);
            if (good_stop) begin
                check(valid_count == old_valid + 1, "Valid RX event missing or duplicate");
                check(error_count == old_error, "Unexpected framing error");
                check(last_received == payload, "RX data mismatch with shifted input phase");
            end else begin
                check(valid_count == old_valid, "Invalid stop wrongly accepted");
                check(error_count == old_error + 1, "Missing or repeated framing error");
                check(rx_data == old_data, "Framing error corrupted stored RX data");
            end
        end
    endtask

    initial begin : scenario
        integer phase, drift, k;
        integer good_frames, bad_frames;
        reg [7:0] values [0:3];
        good_frames = 0;
        bad_frames = 0;
        values[0] = 8'h00;
        values[1] = 8'hff;
        values[2] = 8'h55;
        values[3] = 8'ha6;

        repeat (6) @(negedge clk);
        rst_n = 1'b1;
        repeat (CPB) @(negedge clk);

        // 3 RX phase offsets x 3 sender bit-length offsets x 4 byte patterns.
        // +/- 1 ns per bit is at most 1.25% for CPB=8.
        for (phase = 1; phase <= 4; phase = phase + 1) begin
            if (phase == 2) begin end else begin
                for (drift = -1; drift <= 1; drift = drift + 1) begin
                    for (k = 0; k < 4; k = k + 1) begin
                        expect_frame(values[k], phase, drift, 1'b1);
                        good_frames = good_frames + 1;
                    end
                    expect_frame(8'h39, phase, drift, 1'b0);
                    bad_frames = bad_frames + 1;
                end
            end
        end
        check(good_frames == 36 && bad_frames == 9, "Scenario test counts incorrect");
        check(valid_count == good_frames, "Overall RX valid count incorrect");
        check(error_count == bad_frames, "Overall RX error count incorrect");
        $display("UART_ASYNC_PASS: CPB=%0d good=%0d errors=%0d phases=1,3,4 drift_ns=-1,0,+1",
                 CPB, good_frames, bad_frames);
        $finish;
    end

    initial begin
        #10000000;
        $fatal(1, "UART async phase regression timed out");
    end
endmodule

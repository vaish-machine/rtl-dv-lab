`timescale 1ns/1ps
// Stage 3A: standalone, self-checking wrapper-pin mapping/8N1 smoke test.
// Pure simulation: no shuttle-template tests, no physical/timing signoff.
module tb_tt_um_vaish_uart;
    reg clk = 1'b0;
    always #50 clk = ~clk; // provisional 10 MHz matching exploratory SDC
    reg rst_n = 1'b0;
    reg ena = 1'b1;
    reg [7:0] ui_in = 8'h00;
    reg [7:0] uio_in = 8'b0000_0010; // async RX idle high
    wire [7:0] uo_out;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;
    reg rx_seen = 1'b0;
    integer i;

    tt_um_vaish_uart dut (
        .ui_in(ui_in), .uo_out(uo_out),
        .uio_in(uio_in), .uio_out(uio_out), .uio_oe(uio_oe),
        .ena(ena), .clk(clk), .rst_n(rst_n)
    );

    // Observe one-cycle receive-valid pulse without relying on final state.
    always @(posedge clk) begin
        #1;
        if (uio_out[4] === 1'b1) begin
            if (uo_out !== 8'h5A)
                $fatal(1, "FAIL | RX data mapping | expected 0x5A, observed %h", uo_out);
            rx_seen = 1'b1;
        end
    end

    task send_rx_bit;
        input value;
        begin
            @(negedge clk);
            uio_in[1] = value;
            repeat (16) @(posedge clk);
        end
    endtask

    initial begin
        #2000000;
        $fatal(1, "FAIL | Wrapper smoke-test timeout");
    end

    initial begin
        repeat (5) @(posedge clk);
        #1;
        if (uio_oe !== 8'h3C)
            $fatal(1, "FAIL | Bidirectional OE | got %h, expected 3C", uio_oe);
        if (uio_out[3] !== 1'b1 || uio_out[2] !== 1'b1)
            $fatal(1, "FAIL | Reset idle TX/ready mapping");
        if (uio_out[7:6] !== 2'b00 || uio_out[1:0] !== 2'b00)
            $fatal(1, "FAIL | Unused output pins must drive 0");
        $display("PASS | Wrapper I/O direction | uio_oe=0x3C");

        @(negedge clk);
        rst_n = 1'b1;
        repeat (3) @(posedge clk);

        // TRANSMIT frame: 8N1 0xA5 via ui_in and uio_in[0] strobe.
        @(negedge clk);
        ui_in = 8'hA5;
        uio_in[0] = 1'b1;
        @(posedge clk);
        #1;
        if (uio_out[3] !== 1'b0 || uio_out[2] !== 1'b0)
            $fatal(1, "FAIL | UART TX start or ready handshake");
        @(negedge clk);
        uio_in[0] = 1'b0;
        for (i = 0; i < 8; i = i + 1) begin
            repeat (16) @(posedge clk);
            #1;
            if (uio_out[3] !== ((8'hA5 >> i) & 1'b1))
                $fatal(1, "FAIL | UART TX bit %0d | observed %b", i, uio_out[3]);
        end
        repeat (16) @(posedge clk);
        #1;
        if (uio_out[3] !== 1'b1)
            $fatal(1, "FAIL | UART TX stop bit");
        repeat (16) @(posedge clk);
        #1;
        if (uio_out[2] !== 1'b1)
            $fatal(1, "FAIL | UART TX ready after frame");
        $display("PASS | Wrapper TX frame | 8N1 0xA5 at CPB=16");

        // RECEIVE frame: 8N1 0x5A via asynchronous uio_in[1].
        send_rx_bit(1'b0); // start
        for (i = 0; i < 8; i = i + 1)
            send_rx_bit((8'h5A >> i) & 1'b1);
        send_rx_bit(1'b1); // stop
        repeat (8) @(posedge clk);
        #1;
        if (!rx_seen)
            $fatal(1, "FAIL | RX valid pulse not observed");
        if (uo_out !== 8'h5A)
            $fatal(1, "FAIL | RX data output | observed %h", uo_out);
        if (uio_out[5] !== 1'b0)
            $fatal(1, "FAIL | RX framing error asserted on valid frame");
        $display("PASS | Wrapper RX frame | 8N1 0x5A, valid pulse, no framing error");
        $display("PASS | Stage 3A Tiny Tapeout UART mapping simulation | All checks passed");
        $finish;
    end
endmodule

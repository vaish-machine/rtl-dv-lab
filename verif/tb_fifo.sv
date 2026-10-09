`timescale 1ns/1ps

module tb_fifo #(
    parameter integer DATA_WIDTH = 8,
    parameter integer DEPTH      = 16
);

    logic clk = 1'b0;
    logic rst_n = 1'b0;
    logic wr_en = 1'b0;
    logic [DATA_WIDTH-1:0] wr_data = '0;
    logic rd_en = 1'b0;
    logic [DATA_WIDTH-1:0] rd_data;
    logic full;
    logic empty;
    logic [$clog2(DEPTH+1)-1:0] level;

    logic [DATA_WIDTH-1:0] reference_mem [0:DEPTH-1];
    integer reference_wr_ptr = 0;
    integer reference_rd_ptr = 0;
    integer reference_count = 0;
    logic [DATA_WIDTH-1:0] last_rd_data = '0;

    integer accepted_writes = 0;
    integer accepted_reads = 0;
    integer rejected_writes = 0;
    integer rejected_reads = 0;
    integer simultaneous_mid = 0;
    integer simultaneous_empty = 0;
    integer simultaneous_full = 0;

    logic [31:0] prng = 32'h1ACE_B00C;
    integer i;

    always #5 clk = ~clk;

    fifo #(
        .DATA_WIDTH(DATA_WIDTH),
        .DEPTH(DEPTH)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(wr_en),
        .wr_data(wr_data),
        .rd_en(rd_en),
        .rd_data(rd_data),
        .full(full),
        .empty(empty),
        .level(level)
    );

    function automatic integer next_ptr(input integer ptr);
        begin
            if (ptr == DEPTH - 1)
                next_ptr = 0;
            else
                next_ptr = ptr + 1;
        end
    endfunction

    task automatic check_status;
        begin
            if (level !== reference_count)
                $fatal(1, "level mismatch: expected %0d, got %0d", reference_count, level);
            if (empty !== (reference_count == 0))
                $fatal(1, "empty mismatch at level %0d", reference_count);
            if (full !== (reference_count == DEPTH))
                $fatal(1, "full mismatch at level %0d", reference_count);
            if ((reference_count < 0) || (reference_count > DEPTH))
                $fatal(1, "reference occupancy out of range: %0d", reference_count);
        end
    endtask

    // Drive at the falling edge, model acceptance from pre-edge state,
    // then compare DUT state after the following rising edge.
    task automatic tick(
        input logic write_request,
        input logic read_request,
        input logic [DATA_WIDTH-1:0] write_value
    );
        logic write_ok;
        logic read_ok;
        logic [DATA_WIDTH-1:0] expected_rd_data;
        integer count_before;
        begin
            @(negedge clk);
            wr_en = write_request;
            rd_en = read_request;
            wr_data = write_value;
            #1;

            check_status();
            count_before = reference_count;
            write_ok = write_request && (count_before < DEPTH);
            read_ok = read_request && (count_before > 0);
            expected_rd_data = last_rd_data;

            if (read_request && !read_ok)
                rejected_reads = rejected_reads + 1;
            if (write_request && !write_ok)
                rejected_writes = rejected_writes + 1;

            if (write_request && read_request) begin
                if (count_before == 0)
                    simultaneous_empty = simultaneous_empty + 1;
                else if (count_before == DEPTH)
                    simultaneous_full = simultaneous_full + 1;
                else if (write_ok && read_ok)
                    simultaneous_mid = simultaneous_mid + 1;
            end

            if (read_ok) begin
                expected_rd_data = reference_mem[reference_rd_ptr];
                reference_rd_ptr = next_ptr(reference_rd_ptr);
                accepted_reads = accepted_reads + 1;
            end

            if (write_ok) begin
                reference_mem[reference_wr_ptr] = write_value;
                reference_wr_ptr = next_ptr(reference_wr_ptr);
                accepted_writes = accepted_writes + 1;
            end

            reference_count = reference_count + write_ok - read_ok;

            @(posedge clk);
            #1;
            last_rd_data = expected_rd_data;
            if (rd_data !== last_rd_data)
                $fatal(1, "rd_data mismatch: expected 0x%0h, got 0x%0h", last_rd_data, rd_data);
            check_status();

            wr_en = 1'b0;
            rd_en = 1'b0;
        end
    endtask

    task automatic reset_fifo;
        begin
            @(negedge clk);
            rst_n = 1'b0;
            wr_en = 1'b0;
            rd_en = 1'b0;
            wr_data = '0;
            @(posedge clk);
            #1;
            reference_wr_ptr = 0;
            reference_rd_ptr = 0;
            reference_count = 0;
            last_rd_data = '0;
            if (rd_data !== '0)
                $fatal(1, "rd_data did not clear on reset");
            check_status();
            @(negedge clk);
            rst_n = 1'b1;
        end
    endtask

    initial begin
        if (DATA_WIDTH < 1)
            $fatal(1, "DATA_WIDTH must be at least 1");
        if (DEPTH < 2)
            $fatal(1, "DEPTH must be at least 2");

        reset_fifo();

        // Empty boundary: read is rejected; simultaneous write/read only writes.
        tick(1'b0, 1'b1, '0);
        tick(1'b1, 1'b1, 8'hA0);
        tick(1'b0, 1'b1, '0);

        // Fill, reject overflow, exercise simultaneous traffic at full, then drain.
        for (i = 0; i < DEPTH; i = i + 1)
            tick(1'b1, 1'b0, 8'h10 + i);
        if (!full)
            $fatal(1, "FIFO did not assert full after filling");
        tick(1'b1, 1'b0, 8'hEE);
        tick(1'b1, 1'b1, 8'hE1);
        for (i = 1; i < DEPTH; i = i + 1)
            tick(1'b0, 1'b1, '0);
        if (!empty)
            $fatal(1, "FIFO did not assert empty after draining");
        tick(1'b0, 1'b1, '0);

        // Simultaneous read/write while partially occupied preserves ordering.
        tick(1'b1, 1'b0, 8'h55);
        tick(1'b1, 1'b0, 8'h66);
        tick(1'b1, 1'b1, 8'h77);
        tick(1'b0, 1'b1, '0);
        tick(1'b0, 1'b1, '0);
        tick(1'b0, 1'b1, '0);

        // Deterministic pseudo-random traffic forces many pointer wraps.
        for (i = 0; i < (DEPTH * 20); i = i + 1) begin
            prng = {prng[30:0], prng[31] ^ prng[21] ^ prng[1] ^ prng[0]};
            tick(prng[0], prng[2], prng[15:8]);
        end

        // Reset with queued data, then ensure the FIFO is empty again.
        tick(1'b1, 1'b0, 8'hBC);
        reset_fifo();
        tick(1'b0, 1'b1, '0);

        if (accepted_writes == 0 || accepted_reads == 0 ||
            rejected_writes == 0 || rejected_reads == 0 ||
            simultaneous_mid == 0 || simultaneous_empty == 0 || simultaneous_full == 0)
            $fatal(1, "One or more directed coverage counters were not hit");

        $display("PASS: FIFO DATA_WIDTH=%0d DEPTH=%0d", DATA_WIDTH, DEPTH);
        $display("  accepted writes=%0d reads=%0d", accepted_writes, accepted_reads);
        $display("  rejected writes=%0d reads=%0d", rejected_writes, rejected_reads);
        $display("  simultaneous mid/empty/full=%0d/%0d/%0d",
                 simultaneous_mid, simultaneous_empty, simultaneous_full);
        $finish;
    end

endmodule


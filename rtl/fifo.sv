`timescale 1ns/1ps

module fifo #(
    parameter integer DATA_WIDTH = 8,
    parameter integer DEPTH      = 16
) (
    input  logic                     clk,
    input  logic                     rst_n,
    input  logic                     wr_en,
    input  logic [DATA_WIDTH-1:0]    wr_data,
    input  logic                     rd_en,
    output logic [DATA_WIDTH-1:0]    rd_data,
    output logic                     full,
    output logic                     empty,
    output logic [$clog2(DEPTH+1)-1:0] level
);

    localparam integer PTR_WIDTH = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer LEVEL_WIDTH = (DEPTH > 1) ? $clog2(DEPTH + 1) : 1;
    localparam logic [PTR_WIDTH-1:0] LAST_PTR = PTR_WIDTH'(DEPTH - 1);
    localparam logic [LEVEL_WIDTH-1:0] DEPTH_COUNT = LEVEL_WIDTH'(DEPTH);

    logic [DATA_WIDTH-1:0] storage [0:DEPTH-1];
    logic [PTR_WIDTH-1:0]  wr_ptr;
    logic [PTR_WIDTH-1:0]  rd_ptr;
    logic                  write_accept;
    logic                  read_accept;

    assign full         = (level == DEPTH_COUNT);
    assign empty        = (level == '0);
    assign write_accept = wr_en && !full;
    assign read_accept  = rd_en && !empty;

    // Synchronous active-low reset. Storage is intentionally not reset;
    // entries are valid only when represented by level.
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            wr_ptr  <= '0;
            rd_ptr  <= '0;
            level   <= '0;
            rd_data <= '0;
        end else begin
            if (write_accept) begin
                storage[wr_ptr] <= wr_data;
                if (wr_ptr == LAST_PTR)
                    wr_ptr <= '0;
                else
                    wr_ptr <= wr_ptr + 1'b1;
            end

            if (read_accept) begin
                rd_data <= storage[rd_ptr];
                if (rd_ptr == LAST_PTR)
                    rd_ptr <= '0;
                else
                    rd_ptr <= rd_ptr + 1'b1;
            end

            case ({write_accept, read_accept})
                2'b10: level <= level + 1'b1;
                2'b01: level <= level - 1'b1;
                default: level <= level;
            endcase
        end
    end

endmodule


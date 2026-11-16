// UART 8N1 transmitter. One synchronous active-low reset clock domain.
// Functional baseline: CLKS_PER_BIT >= 8, no FIFO, no parity.
module uart_tx #(
    parameter integer CLKS_PER_BIT = 16
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       tx_valid,
    input  wire [7:0] tx_data,
    output wire       tx_ready,
    output reg        tx_o
);
    localparam integer CW = $clog2(CLKS_PER_BIT);
    // Use a width-matched constant to avoid implicit 32-bit truncation.
    localparam integer LAST_TICK_INT = CLKS_PER_BIT - 1;
    localparam [CW-1:0] LAST_TICK = LAST_TICK_INT[CW-1:0];
    localparam [1:0] S_IDLE = 2'd0, S_START = 2'd1,
                     S_DATA = 2'd2, S_STOP = 2'd3;

    reg [1:0] state;
    reg [CW-1:0] ticks;
    reg [2:0] bit_index;
    reg [7:0] shift_data;

    assign tx_ready = (state == S_IDLE);

    always @(posedge clk) begin
        if (!rst_n) begin
            state      <= S_IDLE;
            ticks      <= {CW{1'b0}};
            bit_index  <= 3'd0;
            shift_data <= 8'd0;
            tx_o       <= 1'b1;
        end else begin
            case (state)
                S_IDLE: begin
                    tx_o <= 1'b1;
                    if (tx_valid) begin
                        shift_data <= tx_data;
                        bit_index  <= 3'd0;
                        ticks      <= {CW{1'b0}};
                        tx_o       <= 1'b0;
                        state      <= S_START;
                    end
                end
                S_START: begin
                    if (ticks == LAST_TICK) begin
                        ticks      <= {CW{1'b0}};
                        tx_o       <= shift_data[0];
                        shift_data <= {1'b0, shift_data[7:1]};
                        state      <= S_DATA;
                    end else begin
                        ticks <= ticks + 1'b1;
                    end
                end
                S_DATA: begin
                    if (ticks == LAST_TICK) begin
                        ticks <= {CW{1'b0}};
                        if (bit_index == 3'd7) begin
                            tx_o  <= 1'b1;
                            state <= S_STOP;
                        end else begin
                            tx_o       <= shift_data[0];
                            shift_data <= {1'b0, shift_data[7:1]};
                            bit_index  <= bit_index + 1'b1;
                        end
                    end else begin
                        ticks <= ticks + 1'b1;
                    end
                end
                S_STOP: begin
                    if (ticks == LAST_TICK) begin
                        ticks <= {CW{1'b0}};
                        state <= S_IDLE;
                    end else begin
                        ticks <= ticks + 1'b1;
                    end
                end
                default: begin
                    state <= S_IDLE;
                    tx_o  <= 1'b1;
                end
            endcase
        end
    end
endmodule

// UART 8N1 receiver; 2-flop async-input synchronizer.
// One-cycle valid or framing-error pulse; invalid stop leaves rx_data intact.
// Break/noisy-stop recovery waits for synchronized idle high.
module uart_rx #(
    parameter integer CLKS_PER_BIT = 16
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx_i,
    output reg  [7:0] rx_data,
    output reg        rx_valid,
    output reg        rx_framing_error
);
    localparam integer CW = $clog2(CLKS_PER_BIT);
    localparam [CW-1:0] LAST_TICK = CLKS_PER_BIT - 1;
    localparam [CW-1:0] HALF_TICK = (CLKS_PER_BIT / 2) - 1;
    localparam [2:0] S_IDLE = 3'd0, S_START = 3'd1,
                     S_DATA = 3'd2, S_STOP = 3'd3,
                     S_WAIT_HIGH = 3'd4;
    reg rx_meta;
    reg rx_sync;
    reg [2:0] state;
    reg [CW-1:0] ticks;
    reg [2:0] bit_index;
    reg [7:0] sampled_data;

    always @(posedge clk) begin
        if (!rst_n) begin
            rx_meta          <= 1'b1;
            rx_sync          <= 1'b1;
            state            <= S_IDLE;
            ticks            <= {CW{1'b0}};
            bit_index        <= 3'd0;
            sampled_data     <= 8'd0;
            rx_data          <= 8'd0;
            rx_valid         <= 1'b0;
            rx_framing_error <= 1'b0;
        end else begin
            rx_meta          <= rx_i;
            rx_sync          <= rx_meta;
            rx_valid         <= 1'b0;
            rx_framing_error <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (!rx_sync) begin
                        ticks <= HALF_TICK;
                        state <= S_START;
                    end
                end
                S_START: begin
                    if (ticks == 0) begin
                        if (!rx_sync) begin
                            ticks       <= CLKS_PER_BIT - 1;
                            bit_index   <= 3'd0;
                            sampled_data <= 8'd0;
                            state       <= S_DATA;
                        end else begin
                            state <= S_IDLE; // reject short low glitch
                        end
                    end else begin
                        ticks <= ticks - 1'b1;
                    end
                end
                S_DATA: begin
                    if (ticks == 0) begin
                        sampled_data[bit_index] <= rx_sync;
                        ticks <= LAST_TICK;
                        if (bit_index == 3'd7) begin
                            state <= S_STOP;
                        end else begin
                            bit_index <= bit_index + 1'b1;
                        end
                    end else begin
                        ticks <= ticks - 1'b1;
                    end
                end
                S_STOP: begin
                    if (ticks == 0) begin
                        if (rx_sync) begin
                            rx_data  <= sampled_data;
                            rx_valid <= 1'b1;
                            state    <= S_IDLE;
                        end else begin
                            rx_framing_error <= 1'b1;
                            state <= S_WAIT_HIGH;
                        end
                    end else begin
                        ticks <= ticks - 1'b1;
                    end
                end
                S_WAIT_HIGH: begin
                    if (rx_sync)
                        state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule

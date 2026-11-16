// UART 8N1 standalone synthesizable digital core.
// Core is technology-independent and has no pad-ring or shuttle interface.
module uart_core #(
    parameter integer CLKS_PER_BIT = 16
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       tx_valid,
    input  wire [7:0] tx_data,
    output wire       tx_ready,
    output wire       tx_o,
    input  wire       rx_i,
    output wire [7:0] rx_data,
    output wire       rx_valid,
    output wire       rx_framing_error
);
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_tx (
        .clk(clk), .rst_n(rst_n),
        .tx_valid(tx_valid), .tx_data(tx_data),
        .tx_ready(tx_ready), .tx_o(tx_o)
    );

    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_rx (
        .clk(clk), .rst_n(rst_n), .rx_i(rx_i),
        .rx_data(rx_data), .rx_valid(rx_valid),
        .rx_framing_error(rx_framing_error)
    );
endmodule

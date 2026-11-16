// SPDX-License-Identifier: Apache-2.0
// Stage 3A: Tiny Tapeout SKY130 UART wrapper *candidate*, NOT a submission.
// Exact official TinyTapeout/ttsky-verilog-template interface (checked 2026-11-16).
// Maps existing unmodified uart_core to TT's 8 dedicated inputs, 8 outputs,
// eight configurable bidirectional pins, clk and rst_n.
`default_nettype none

module tt_um_vaish_uart (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    wire       tx_ready;
    wire       tx_o;
    wire [7:0] rx_data;
    wire       rx_valid;
    wire       rx_framing_error;

    // Dedicated inputs carry the complete parallel TX byte.
    // Bidirectional pins 0,1 are INPUTs: TX strobe and asynchronous UART RX.
    // Bidirectional pins 2..5 are OUTPUTs: ready, serial TX, RX valid, error.
    // Dedicated outputs carry the complete parallel RX byte.
    uart_core #(.CLKS_PER_BIT(16)) u_uart (
        .clk              (clk),
        .rst_n            (rst_n),
        .tx_valid         (uio_in[0]),
        .tx_data          (ui_in),
        .tx_ready         (tx_ready),
        .tx_o             (tx_o),
        .rx_i             (uio_in[1]),
        .rx_data          (rx_data),
        .rx_valid         (rx_valid),
        .rx_framing_error (rx_framing_error)
    );

    assign uo_out  = rx_data;
    assign uio_out = {2'b00, rx_framing_error, rx_valid, tx_o, tx_ready, 2'b00};
    assign uio_oe  = 8'b0011_1100;  // pins [5:2] output, [1:0], [7:6] input

    // The official SKY template specifies 'ena' high while powered/enabled.
    // Do NOT gate an already-running UART clock with ena.
    wire _unused = &{ena, uio_in[7:2], 1'b0};
endmodule
`default_nettype wire

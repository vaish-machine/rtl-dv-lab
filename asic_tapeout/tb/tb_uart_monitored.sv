// Stage 1C harness: reuse the proven Stage 1B traffic generator unchanged.
// Additional pin-only protocol assertions + scenario-hit count gate.
// Scenario counters are stimulus/scoreboard hit evidence, NOT functional coverage closure.
module tb_uart_monitored;
    parameter integer CPB = 16;
    tb_uart_stress #(.CPB(CPB)) traffic();

    uart_tx_pin_checker #(.CPB(CPB)) tx_check (
        .clk(traffic.clk), .rst_n(traffic.rst_n),
        .tx_valid(traffic.tx_valid), .tx_ready(traffic.tx_ready),
        .tx_o(traffic.tx_o), .tx_data(traffic.tx_data)
    );
    uart_rx_pin_checker loop_rx_check (
        .clk(traffic.clk), .rst_n(traffic.rst_n),
        .rx_data(traffic.loop_data),
        .rx_valid(traffic.loop_valid),
        .rx_framing_error(traffic.loop_error)
    );
    uart_rx_pin_checker direct_rx_check (
        .clk(traffic.clk), .rst_n(traffic.rst_n),
        .rx_data(traffic.direct_data),
        .rx_valid(traffic.direct_valid),
        .rx_framing_error(traffic.direct_error)
    );

    reg coverage_reported = 1'b0;
    always @(negedge traffic.clk) begin
        if (!coverage_reported &&
            traffic.loop_count == 60 &&
            traffic.direct_count == 73 &&
            traffic.error_count == 4) begin
            if (tx_check.tx_accepted != 60)
                $fatal(1, "UART_ASSERT_FAIL: TX handshake count expected 60, got %0d", tx_check.tx_accepted);
            coverage_reported = 1'b1;
            $display("UART_SCENARIO_HITS_PASS: CPB=%0d tx_handshakes=%0d loop=%0d direct=%0d framing_errors=%0d",
                     CPB, tx_check.tx_accepted,
                     traffic.loop_count, traffic.direct_count, traffic.error_count);
        end
    end
endmodule

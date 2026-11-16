# Stage 2F, exploratory UART SKY130 digital core timing constraints.
# All budgets below are provisional and NOT host-board or shuttle assumptions.
# Design: synchronous active-low rst_n; tx_valid/tx_data are synchronous to clk.
# rx_i is asynchronous external serial data entering uart_rx.rx_meta (first
# register in a two-flop synchronizer). Input-to-first-flop path is excepted.
# The rx_meta -> rx_sync register-to-register path is NOT false-pathed.
#
# STA units follow the selected SKY130 liberty (typically ns and pF);
# verify against the actual PDK before release signoff.

create_clock -name uart_clk -period 100.0 [get_ports clk]
set_clock_uncertainty 0.30 [get_clocks uart_clk]
set_clock_transition 0.10 [get_clocks uart_clk]

# Host-visible parallel TX handshake and synchronous reset.
# Provisional external setup and hold budgets: arrival 0..10 ns.
foreach port_pattern {rst_n tx_valid tx_data*} {
    set p [get_ports $port_pattern]
    if {[llength $p] == 0} {
        error "Missing expected synchronous UART input: $port_pattern"
    }
    set_input_delay -max 10.0 -clock [get_clocks uart_clk] $p
    set_input_delay -min 0.0 -clock [get_clocks uart_clk] $p
    set_input_transition 0.10 $p
}

# Digital core outputs, not pads. Provisional 10 ns external delay and
# 0.01 pF load: replace with actual wrapper loads and IO constraints.
foreach port_pattern {tx_ready tx_o rx_data* rx_valid rx_framing_error} {
    set p [get_ports $port_pattern]
    if {[llength $p] == 0} {
        error "Missing expected UART output: $port_pattern"
    }
    set_output_delay -max 10.0 -clock [get_clocks uart_clk] $p
    set_output_delay -min 0.0 -clock [get_clocks uart_clk] $p
    set_load 0.01 $p
}

# Do not invent setup/hold timing relationship to async serial rx_i.
# RTL places only rx_meta before rx_sync; do not suppress rx_meta->rx_sync.
set_false_path -from [get_ports rx_i]

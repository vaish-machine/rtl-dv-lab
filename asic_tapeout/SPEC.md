# UART 8N1 Core — Functional Baseline v0.2 (candidate, G1 review pending)

This version provides the functional assumptions for an initial **synthesizable RTL candidate and directed self-checking testbench**, not a frozen tapeout/shuttle specification. Verify and review behavior before marking G1 complete.

## Scope and protocol

- Independent TX and RX, full duplex, single clock domain; no FIFO, parity, CTS/RTS, APB, DMA or interrupts.
- Serial idle 1; each frame has start=0, eight data bits LSB first, stop=1 (8N1).
- Each start, data and stop bit occupies exactly CLKS_PER_BIT clock cycles at TX output.
- CLKS_PER_BIT is an integer >= 8. Initial test configurations: 16 and 8. Frequency, baud and allowable baud mismatch depend on future constraints.
- rst_n is an **active-low synchronous reset**, evaluated on the rising edge of clk.
- rx_i is potentially asynchronous and passes through two flip-flops before RX logic. This does not prove CDC/metastability signoff.

## Interface: uart_core

| Port | Direction | Functional contract |
|---|---|---|
| clk | input | Rising-edge sampling |
| rst_n | input | Synchronous active-low reset |
| tx_valid | input | Request; accepted only with tx_ready at a rising edge |
| tx_data[7:0] | input | Latched at acceptance; busy changes ignored |
| tx_ready | output | High only in TX idle; low through stop bit |
| tx_o | output | High during idle/reset; otherwise TX waveform |
| rx_i | input | Asynchronous serial input |
| rx_data[7:0] | output | Last valid RX byte; unchanged on invalid stop |
| rx_valid | output | One-cycle pulse for good stop |
| rx_framing_error | output | One-cycle pulse for bad stop |

## Receiver behavior

1. Detect a synchronized low start.
2. Reject a start whose synchronized level is high at the nominal half-bit start sample.
3. Sample eight data bits near centres, each one bit period apart.
4. At stop centre, emit either rx_valid or rx_framing_error, never both.
5. On invalid stop, wait for synchronized RX high before new start detection (break recovery).
6. Reset discards a pending frame and clears pulses; stored rx_data becomes zero.

## Files and initial tests

- rtl/uart_tx.sv — TX state machine.
- rtl/uart_rx.sv — RX synchronizer and sample state machine.
- rtl/uart_core.sv — technology-independent top.
- tb/tb_uart_core.sv — independent waveform checks, loopback and externally driven RX stimulus.
- scripts/run-uart-baseline-wsl.sh — Icarus simulation at 8 and 16 cycles per bit, lint, generic synthesis.

**Current state:** Candidate source and tests committed, but UART test results on the user's PC have not yet been received. Do not claim passing UART simulation, lint or synthesis until executed.

## Outstanding before G1 freeze and G2 verification closure

- Shuttle/harness selection, physical clock, target baud and allowable mismatch.
- Reset/recovery contract, IO levels, reset strategy, timing constraints and area budget.
- Back-to-back frames, independent simultaneous TX/RX, RX reset in every phase, baud/phase offsets and deterministic randomized sequences.
- Assertions, coverage closure, CDC review, reset/power-up analysis, and reviewed timing/area evidence.
- Confirm actual supported parameter range by test and physical constraints.
- Generic Yosys synthesis is not SKY130 mapping, P&R, DRC/LVS, signoff or fabrication submission.

Never infer measured area/power/timing or shuttle acceptance from this functional baseline.

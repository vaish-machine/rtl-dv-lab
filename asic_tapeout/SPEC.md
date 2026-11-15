# UART 8N1 Core Specification v0.1 — DRAFT, NOT FROZEN

Implement a small, single-clock synthesizable digital UART TX/RX core as the first full physical-flow test vehicle. This is a **core**, not yet a pad-ring ASIC or a shuttle harness.

## Protocol
- Idle serial level 1; start bit 0; eight data bits LSB first; no parity; one stop bit 1.
- Full duplex transmit and receive; no FIFO, APB, interrupts, DMA or flow control in v1.
- Compile-time integer CLKS_PER_BIT >= 8, calculated from target clock and baud; physical/shuttle clock TBD.
- One clk domain and synchronous active-low rst_n. RX asynchronous input goes through a two-flop synchronizer before sampling.
- TX accepts a byte only on rising-edge tx_valid && tx_ready; latches it; ignores further requests while busy; each bit holds CLKS_PER_BIT clocks.
- RX confirms low start near its centre and samples data bits near their centres; rx_valid pulses for one clock on a valid frame; framing_error pulses on invalid stop; rx_data changes only for a valid byte. Back-to-back frames supported.
- Reset returns TX output high and clears any active transfer/valid/error state.

## Proposed core ports
| Signal | Direction | Meaning |
|---|---|---|
| clk | input | Core clock |
| rst_n | input | Synchronous active-low reset |
| tx_valid | input | Start request |
| tx_data[7:0] | input | Byte to send |
| tx_ready | output | Can accept next byte |
| tx_o | output | Serial TX (idle high) |
| rx_i | input | External asynchronous RX |
| rx_data[7:0] | output | Most recently received valid byte |
| rx_valid | output | Single-cycle receive event |
| rx_framing_error | output | Single-cycle invalid-stop event |

## Deliberately unresolved before G1
Shuttle choice and official compatible pin wrapper; exact clock frequency and divider; reset and break recovery; allowable baud error; area, timing, power and PVT corners; final physical constraints. Do not invent measured PPA targets.

## Verification obligations
Independent UART testbench must cover bit periods/order, all critical data patterns, TX busy handling, RX malformed start/stop and recovery, back-to-back frames, resets in each phase, simultaneous TX/RX, asynchronous RX edge offsets and supported divider limits.

**Spec is planning-only until explicitly reviewed and frozen in a later commit.**
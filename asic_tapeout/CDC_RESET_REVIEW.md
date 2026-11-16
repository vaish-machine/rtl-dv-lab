# UART CDC and reset architectural review — preliminary v0.1

**Status: engineering analysis only, NOT a CDC signoff or silicon approval.**
This review applies to the initial RTL candidate at rtl/uart_rx.sv, rtl/uart_tx.sv and rtl/uart_core.sv. The observed user-machine Stage 1A–1D tests cannot establish metastability behavior, path constraints or PVT timing.

## Clock and asynchronous input inventory

| Item | Clock domain / nature | RTL treatment | Remaining action |
|---|---|---|---|
| clk | Single external core clock | All UART FSM and data registers update at posedge clk | Choose real frequency and shuttle clock source; constrain in SDC |
| rst_n | Synchronous active-low control | Reset tested inside posedge always blocks for both TX and RX | Decide physical reset source, asynchronous assertion needs and release policy |
| rx_i | External serial, may transition asynchronously | First stage rx_meta, second stage rx_sync (two flip-flops, both clocked by clk) | Define synchronized flop placement/attributes, STA false-path to first stage only, metastability MTBF assumptions |
| tx_valid, tx_data | Assumed synchronous to clk | Sample tx_valid && tx_ready at posedge clk | If driven from an independent clock domain, add handshake/FIFO CDC; cannot treat multi-bit tx_data as independently synchronized |
| tx_o | Registered serial TX output | Bit timing controlled by clk | Constrain output to actual pad/shuttle environment |
| rx_data, rx_valid, rx_framing_error | Synchronous to clk | Updated in RX clock domain | If sampled in another clock domain, external CDC is required |

## Two-flop synchronizer limitations

- rx_meta and rx_sync are logically two distinct clk-domain registers in the RTL. This reduces, but does not eliminate, metastability propagation risk.
- The first-stage rx_meta input arrives from outside clk. ASIC implementation must preserve a two-stage synchronizer structure and place stages appropriately; use the target flow's documented asynchronous-register recognition/constraints rather than blindly applying vendor-specific FPGA attributes.
- STA constraints: create the source clock; treat rx_i to the FIRST synchronizer flop as an asynchronous path per the chosen methodology. Do **not** globally false-path all RX logic or the path between rx_meta and rx_sync: synchronizer settling time matters.
- MTBF requires a specific cell library, resolution/clock periods, RX transition-rate assumptions, layout and PVT characterization. **No MTBF number is available**.
- Dynamic RX phase tests (Stage 1C) explore nanosecond digital timing offsets; they do not model analog metastability or a multi-clock CDC implementation.

## Reset assumptions and physical integration

- The functional specification defines synchronous active-low rst_n. An asserted rst_n does not force outputs until a rising clk edge; first power-up behavior without a known reset clock edge is NOT guaranteed.
- Stage 1D explicitly checked resets during nominal start, each of 8 data-bit intervals and stop at four divider values. It is NOT exhaustive for all clock-edge permutations or reset glitches.
- The RX synchronizer initializes rx_meta/rx_sync to idle high on the reset clock edge, suppressing false low-start detection while reset is effective.
- If rst_n comes from a genuinely asynchronous source, the surrounding chip must guarantee correct assertion and deassertion handling to the single-clock UART, including recovery/removal constraints as applicable.
- Source vs sink timing, IO pin/pad levels, ESD protection and board/system reset requirements are not defined by the UART core alone.

## Signoff blockers (explicit)

1. Choose shuttle and physical clock frequency/baud; review associated CLK and reset IO constraints.
2. Define synchronous timing assumptions for tx_valid/tx_data and destination domain of rx_data/events. If there is more than one clock domain, add valid multi-bit CDC structures.
3. Create and audit SDC input/output and false-path constraints with the PDK and actual top wrapper.
4. Run a CDC-specific structural/report check where available; independently inspect synthesis netlist preservation of rx_meta -> rx_sync and report any transformations.
5. Inspect synchronizer placement/routing and physical timing; review MTBF and data validity under selected PVT corners.
6. Define reset assertion and release policy, and verify it at wrapper/top integration level.

**Review outcome:** single core clock and a two-flop input synchronizer form a reasonable initial UART architecture. The design is *not CDC-clean by signoff evidence* until the above integration-dependent checks are complete.

## Formal verification scope

Stage 1E adds bounded Yosys SMTBMC safety checks for TX handshake/idle and RX data/event behavior under arbitrary sampled input values after an initial synchronous reset. It does not establish metastability behavior, full-frame liveness, analog glitch tolerance, asynchronous clock-domain crossing quality or shuttle suitability. Its pass/fail is PENDING until actual user-machine logs are available.

Relevant Yosys documentation:
- https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/index_formal.html
- https://github.com/YosysHQ/yosys/blob/main/docs/source/using_yosys/verilog.rst

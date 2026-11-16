# Self-checking verification plan v0.2 — G2 OPEN

Tests must derive expected results independently of DUT internals, fail on every mismatch and record seeds, versions, trace and source commit.

- RTL lint: widths, latch checks, driver conflicts, reset and synthesis issues; review warning waivers.
- TX directed: 0x00/0xFF/0x55/0xAA/0x01/0x80; bit order, exact CLKS_PER_BIT timing, busy requests, reset mid-frame.
- RX directed: clean frames, start glitch, broken stop/framing error, idle gaps, back-to-back frames, held-low break and recovery, RX near clock edges.
- Random: reproducible randomized bytes, gaps, RX phase offsets and full-duplex overlap.
- Assertions: idle/reset invariant, valid-ready handshake, one-cycle rx_valid/error, mutual exclusion of rx_valid and error, legal state progression, bounded frame completion under stated assumptions.
- Functional coverage: TX/RX byte classes; reset in each state; start/data/stop; framing errors; busy requests; continuous frames; simultaneous TX/RX; divider corners.
- Review independent model, testbench clocking/races, exclusions and coverage closure. 100% code or functional coverage alone is never proof of correctness.
- Gate-level or equivalence check when supported; run final wrapper regression in the actual shuttle template.

Accept G2 only with clean mandatory tests, achieved mandatory bins, no known design mismatches, reviewed warnings and archived pass/fail evidence. No tests have been executed as part of this planning commit.
## Initial directed RTL baseline (Stage 1A — prepared, unexecuted)

- [ ] Icarus SystemVerilog self-checking baseline at 16 clocks/bit.
- [ ] Icarus same testbench at 8 clocks/bit.
- [ ] TX exact start/data/stop timing and bit order; bytes 00/FF/55/AA/01/80, plus busy-request rejection and post-reset recovery.
- [ ] TX-to-RX internal loopback accepted data and strobes.
- [ ] Independent RX serial stimulus: valid 00/FF/55/AA/80/96, short start glitch rejection, invalid stop pulse and data preservation, recovery.
- [ ] Verilator -Wall lint of UART core and its TX/RX components.
- [ ] Yosys generic synthesis/check of UART top (not SKY130 mapped).
- [ ] All logs include tool versions, parameters, commit hash and explicit PASS/FAIL markers.

Sources: rtl/uart_tx.sv, rtl/uart_rx.sv, rtl/uart_core.sv, tb/tb_uart_core.sv. Run through scripts/run-uart-baseline-wsl.sh; store generated output under G: Temp, not source repo. Current tests are **candidates, not results**.

## Additional G2 exit criteria beyond Stage 1A

- [ ] True back-to-back RX and TX without an idle gap; verified independent simultaneous full-duplex traffic.
- [ ] Reset insertion during every RX phase and all TX phases; stuck-low/break recovery.
- [ ] Deterministic randomized payload, timing and phase stress with logged seeds, independent scoreboard.
- [ ] Additional baud divider corner values and baud mismatch acceptance/rejection limits.
- [ ] Assertions and functional coverage bins, including transitions and error corner cases.
- [ ] CDC/metastability treatment, reset synchrony, synchronizer constraints and integration review.
- [ ] Reviewed waivers, formal/equivalence where feasible, audited failing tests and final signoff evidence.

**No UART regression test has been reported passing yet.** The earlier Stage 0I counter simulation/lint/synthesis was a separate toolchain smoke test.

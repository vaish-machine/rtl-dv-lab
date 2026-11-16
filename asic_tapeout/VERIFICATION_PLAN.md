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

- [x] Icarus SystemVerilog self-checking baseline at 16 clocks/bit (user-provided Stage 1A PASS).
- [x] Icarus same testbench at 8 clocks/bit (user-provided Stage 1A PASS).
- [ ] TX exact start/data/stop timing and bit order; bytes 00/FF/55/AA/01/80, plus busy-request rejection and post-reset recovery.
- [ ] TX-to-RX internal loopback accepted data and strobes.
- [ ] Independent RX serial stimulus: valid 00/FF/55/AA/80/96, short start glitch rejection, invalid stop pulse and data preservation, recovery.
- [x] Verilator -Wall lint of UART core and its TX/RX components (user-provided Stage 1A PASS).
- [x] Yosys generic synthesis/check of UART top (user-provided Stage 1A PASS; not SKY130 mapped).
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

**Stage 1A complete:** Icarus directed regressions CPB=16 and 8, Verilator -Wall lint and Yosys generic synthesis have PASS results from the user's environment. Further verification below remains open. The earlier Stage 0I counter smoke was separate.

## Stage 1B — extended deterministic stress (PASS on user's WSL machine)

New independent interface-level testbench: `tb/tb_uart_stress.sv`; controlled runner: `scripts/run-uart-stress-wsl.sh`. Planned runs span `CLKS_PER_BIT` 8, 9, 16 and 32 with reproducible decimal seeds 20261116 and 20261117 (8 total configurations). The stress test exercises pseudo-random TX bytes, illegitimate TX_VALID requests while busy, 50 consecutive external RX bytes without extra idle clocks, malformed stops/data preservation, short-start glitch, long break recovery, reset during RX, and parallel independent TX and RX transactions. The scoreboard sees **only top-level interfaces**, not DUT internal FSMs or counters. Generated files and logs go under G: Temp, source clone is fast-forwarded only if clean and on expected main.

- [x] Stage 1B: all 8/8 simulation configurations PASS (user-provided log from 2026-11-16, seeds 20261116/20261117, CPB 8/9/16/32).
- [ ] Review unexpected behavior and testbench timing/race limitations, even if PASS.
- [ ] Additional independent asynchronous phase/baud-offset stress and coverage still required.
- [ ] Parameter corner and bounded formal checks before G2 closure.

Stage 1B PASS is based on execution output supplied from the user's Ubuntu machine, not on GitHub commit status. This does not establish full verification closure or PDK-mapped signoff.


## Stage 1C — pin checkers, scenario-hit counts and asynchronous phase (PREPARED, NOT RUN)

Source: tb/uart_interface_checkers.sv (Icarus-compatible **procedural interface assertions**, not IEEE SVA/formal proof), tb/tb_uart_monitored.sv, tb/tb_uart_async_phase.sv, scripts/run-uart-assertions-phase-wsl.sh.

- [ ] All 8 repeatable monitored Stage 1B stress configurations PASS, with a black-box reference checker validating exact TX start/data/stop timing, tx_ready timing and accepted bytes.
- [ ] Both independent RX interfaces satisfy one-cycle valid/error pulses, mutual exclusivity, and stored rx_data immutability except on valid frame or reset.
- [ ] Scenario-hit gate: TX accepted handshakes 60, loopback frames 60, independent RX good frames 73 and framing errors 4 for each stress configuration. These are a **small set of observed scenario counts**, not comprehensive functional coverage.
- [ ] Additional independent off-clock serial stimuli: start transitions 1, 3 and 4 ns after a falling clock; transmitter bit duration CPB*10 ns plus -1/0/+1 ns drift. For each CPB=8/9/16/32, check 36 valid frames and nine bad-stop events.
- [ ] Review checker assumptions and residual gaps, including CDC/metastability MTBF, input transition jitter wider than test envelope, reset during every RX state, response to arbitrary baud mismatch and real shuttle IO constraints.

Actual user WSL results are required before any Stage 1C item is marked PASS. These checks are simulation evidence, not proof of formal completeness or physical implementation.

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

- [x] All 8 repeatable monitored Stage 1B stress configurations PASS on the user's workstation (Stage 1C original); **checker timebase fix pending revalidation in Stage 1D**.
- [x] Both independent RX interfaces checked in the Stage 1C original run; **off-clock checker timebase corrected, pending revalidation in Stage 1D**.
- [x] Stage 1C scenario-hit gate PASS across eight configurations (TX accepted=60, loopback=60, direct RX=73, framing errors=4 per run). These are **scenario counts**, not comprehensive functional coverage.
- [x] Stage 1C off-clock serial stimuli PASS for CPB=8/9/16/32 with 36 valid frames and 9 bad stops each; **RX pin checker had unspecified timescale in original run, so Stage 1D will recheck with explicit 1 ns sample timing**.
- [ ] Review checker assumptions and residual gaps, including CDC/metastability MTBF, input transition jitter wider than test envelope, reset during every RX state, response to arbitrary baud mismatch and real shuttle IO constraints.

Original Stage 1C results were supplied as 12/12 PASS by the user, with clean working tree. Review identified an implicit timescale in the shared checker used with a nanosecond-timed async stimulus; fix committed and its actual effectiveness must be revalidated. Simulation evidence is not formal completeness or physical signoff.


## Stage 1D — timed checker revalidation and UART reset-phase coverage (PASS)

- [x] Revalidated the complete Stage 1C eight monitored stress + four asynchronous RX configurations (12/12 PASS, explicit 1ns checker timescale).
- [x] Independent 8N1 black-box reset test passed for early reset at start/eight-data/stop intervals, TX and RX separately.
- [x] Verified TX recovery and RX no-spurious-event + recovery after reset per phase.
- [x] Reset matrix PASS at CPB 8/9/16/32 (4/4 runs, 80 phase/configuration tuples, clean Git tree).
- [x] Recorded actual user-machine PASS output (no reported failed assertions), local G: log `ASIC-Stage1D-UART-20261116-051307.log`. Assertion sampling is scoped to the implemented testbench and still merits independent review.

Sources: tb/tb_uart_reset_matrix.sv, tb/uart_interface_checkers.sv, scripts/run-uart-reset-matrix-wsl.sh. This is **directed reset coverage**, not a final functional coverage percentage. CDC/MTBF, exhaustive formal checks, broad reset-edge exploration, post-synthesis equivalence and full PDK/physical signoff are still pending. Stage 1D PASS is based on the user's executed WSL output. Reset-phase scenario hits are not a functional coverage percentage or exhaustive formal proof.


## Stage 1E — preliminary bounded safety formal (PASSED in bounded scope) and CDC review (OPEN)

- [x] Verified yosys-smtbmc / Yosys 0.33 and Z3 4.8.12 on user's Ubuntu.
- [x] Four BMC safety checks PASSED: UART TX and RX at CPB 8 and 16, each 32 sampled steps with initial synchronous reset assumption.
- [x] TX handshake reachability cover PASSED.
- [x] Recorded user-provided solver PASS outcomes; source head `948740b6defe` with clean working tree; no counterexample reported.
- [ ] Review [CDC_RESET_REVIEW.md](CDC_RESET_REVIEW.md) and leave integration-dependent CDC, timing, synchronizer placement, reset release and physical signoff OPEN.

Files: formal/uart_formal_safety.sv, scripts/run-uart-formal-wsl.sh. **Stage 1E has user-provided 4/4 BMC PASS plus TX cover PASS.** A 32-step bound is shorter than an entire 8N1 frame at CPB=8/16; no full-frame liveness, unbounded proof or analog CDC evidence is established.

## Remaining G2 verification exit gates

- [ ] Review and freeze UART clock, baud, reset, divider support and wrapper timing assumptions (G1), then revisit tests using actual planned operating points.
- [ ] Decide on stronger inductive/formal properties for **complete TX/RX frames**, or explicitly document bounded-only limitations in final design review.
- [ ] Collect useful branch/FSM/toggle coverage or documented equivalent and analyze missing bins. Scenario hit counts alone are not a percentage.
- [ ] Review and sign off synthesizer preservation/placement of input synchronizer, CDC/MTBF assumptions and IO/reset timing constraints in the actual technology/harness.
- [ ] Retest official shuttle wrapper and PDK-mapped netlist against RTL golden behavior, plus timing signoff.

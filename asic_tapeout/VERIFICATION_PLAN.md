# Self-checking verification plan v0.1 — PENDING

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
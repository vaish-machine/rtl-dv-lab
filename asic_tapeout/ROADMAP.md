# 45-day working plan (6–8 focused hours/day; estimate, not a guarantee)

| Days | Work | Gate to pass |
|---|---|---|
| 01–03 | Inspect Windows/WSL2/resources; pick target shuttle and clock; freeze spec | G0 environment; G1 signed-off versioned spec |
| 04–09 | RTL TX/RX, unit tests and lint | Clean lint and directed waveforms |
| 10–16 | Self-checking UVM and/or cocotb, SVA, random regression and coverage | Required directed/random tests and mandatory bins pass |
| 17–20 | Independent reference model review; reset, CDC and formal checks as supported | Verification review completed, limitations documented |
| 21–25 | Yosys synthesis, SKY130 mapping, SDC and pre-route STA | Netlist, utilization and timing reports reviewed |
| 26–34 | Floorplanning, power plan, placement, CTS, routing | Reproducible post-route database and logs |
| 35–40 | Post-route STA, DRC/LVS, other applicable signoff checks; fix violations | No unresolved blocking violations in available applicable checks |
| 41–45 | Official shuttle wrapper/template, provider tests/CI, packaging and submission | Acceptance only if provider confirms; otherwise report blocker |

Rules:
1. Never count a GitHub commit as proof the associated tool ran.
2. Do not move past verification into implementation with known functional failures.
3. Keep command, tool version, PDK revision, commit SHA, pass/fail log, reports and known exceptions for every gate.
4. Distinguish a hardened design/macro from a complete standalone chip, and a passing flow from foundry-qualified signoff.
5. A tapeout claim requires evidence of an accepted fabrication submission; silicon claims require receiving and testing hardware.

Risk: time increases if WSL/PDK installation fails, if physical signoff is difficult, or if the selected shuttle has restrictive area/IO rules. Foundry manufacturing takes additional months.
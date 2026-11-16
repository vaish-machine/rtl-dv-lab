#!/usr/bin/env bash
# ASIC Stage 1C — portable black-box assertions, scenario hits, async RX phase.
# Guarded clean fast-forward; no generated files inside repo; all logs on G:.
set -Eeuo pipefail
ROOT="/mnt/g/C-Drive-Backup-PreReset/Temp"
REPO="$HOME/projects/rtl-dv-lab"
echo "===== ASIC STAGE 1C: UART ASSERTIONS AND RX PHASE ====="
if [[ ! -d "$ROOT" ]]; then
    echo "FAIL | G: Temp not mounted; no changes made"
    exit 1
fi
LOG="$ROOT/ASIC-Stage1C-UART-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
fail() {
    printf 'FAIL | %s\n' "$1"
    printf 'FAIL | %s\n' "$1" >> "$LOG"
    echo "===== COMPACT TEST ERROR DETAILS ====="
    grep -Ei 'UART_ASSERT_FAIL|UART_ASYNC_FAIL|UART_STRESS_FAIL|FATAL|error:|^%Warning|^%Error|syntax error|warning:' "$LOG" | tail -n 12 || true
    echo "===== END TEST ERROR DETAILS ====="
    echo "INFO | Detailed log: $LOG"
    exit 1
}
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
[[ "$(id -un)" == "vaish" && "$(id -u)" != "0" ]] || fail "Expected normal Ubuntu user vaish"
for tool in git iverilog vvp; do
    command -v "$tool" >/dev/null 2>&1 || fail "Missing executable $tool"
done
[[ -d "$REPO/.git" ]] || fail "Expected rtl-dv-lab clone not found"
[[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Expected main branch"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] || fail "Unexpected Git origin"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "Checkout not clean; refused update"
report PASS "Git checkout" "main, clean, expected origin"
if ! git -C "$REPO" fetch origin main >> "$LOG" 2>&1; then
    fail "Git fetch failed"
fi
if ! git -C "$REPO" merge-base --is-ancestor HEAD origin/main; then
    fail "Git checkout diverged; no merge attempted"
fi
if ! git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1; then
    fail "Git fast-forward failed"
fi
report PASS "Fast-forward HEAD" "$(git -C "$REPO" rev-parse --short=12 HEAD)"
DESIGN="$REPO/asic_tapeout"
for source in rtl/uart_tx.sv rtl/uart_rx.sv rtl/uart_core.sv \
    tb/uart_interface_checkers.sv tb/tb_uart_stress.sv \
    tb/tb_uart_monitored.sv tb/tb_uart_async_phase.sv; do
    [[ -f "$DESIGN/$source" ]] || fail "Required design/test source missing: $source"
done
WORK="$(mktemp -d "$ROOT/ASIC-Stage1C-UART.XXXXXXXX")"
cd "$WORK"
report INFO "Workspace" "$WORK"
report INFO "Assertion scope" "TX exact 8N1 waveform/ready; RX event pulse/exclusion/data hold; directed scenario hit counts"
report INFO "RX phase scope" "Phases 1,3,4 ns after falling edge; per-bit sender deviation -1,0,+1 ns"

STRESS_TOTAL=0
for cpb in 8 9 16 32; do
    if ! iverilog -g2012 -s tb_uart_monitored -Ptb_uart_monitored.CPB="$cpb" \
        -o "$WORK/monitored_$cpb.vvp" \
        "$DESIGN/rtl/uart_tx.sv" "$DESIGN/rtl/uart_rx.sv" "$DESIGN/rtl/uart_core.sv" \
        "$DESIGN/tb/uart_interface_checkers.sv" \
        "$DESIGN/tb/tb_uart_stress.sv" "$DESIGN/tb/tb_uart_monitored.sv" >> "$LOG" 2>&1; then
        fail "Monitored Icarus compilation failed: CPB=$cpb"
    fi
    for seed in 20261116 20261117; do
        testlog="$WORK/monitored_$cpb-$seed.log"
        if ! vvp "$WORK/monitored_$cpb.vvp" "+SEED=$seed" > "$testlog" 2>&1; then
            cat "$testlog" >> "$LOG"
            fail "Monitored UART simulation failed: CPB=$cpb seed=$seed"
        fi
        cat "$testlog" >> "$LOG"
        if ! grep -q "^UART_STRESS_PASS: CPB=$cpb SEED=$seed " "$testlog" ||
           ! grep -q "^UART_SCENARIO_HITS_PASS: CPB=$cpb tx_handshakes=60 loop=60 direct=73 framing_errors=4$" "$testlog"; then
            fail "Required stress/assertion/coverage marker absent: CPB=$cpb seed=$seed"
        fi
        STRESS_TOTAL=$((STRESS_TOTAL + 1))
        report PASS "UART pin assertions" "CPB=$cpb seed=$seed; scenario-hit count checked"
    done
done
report PASS "Monitored stress configurations" "$STRESS_TOTAL / 8"

PHASE_TOTAL=0
for cpb in 8 9 16 32; do
    if ! iverilog -g2012 -s tb_uart_async_phase -Ptb_uart_async_phase.CPB="$cpb" \
        -o "$WORK/phase_$cpb.vvp" \
        "$DESIGN/rtl/uart_rx.sv" "$DESIGN/tb/uart_interface_checkers.sv" \
        "$DESIGN/tb/tb_uart_async_phase.sv" >> "$LOG" 2>&1; then
        fail "Async phase compile failed: CPB=$cpb"
    fi
    testlog="$WORK/phase_$cpb.log"
    if ! vvp "$WORK/phase_$cpb.vvp" > "$testlog" 2>&1; then
        cat "$testlog" >> "$LOG"
        fail "Async RX phase regression failed: CPB=$cpb"
    fi
    cat "$testlog" >> "$LOG"
    if ! grep -q "^UART_ASYNC_PASS: CPB=$cpb good=36 errors=9 " "$testlog"; then
        fail "Async RX phase result/coverage marker absent: CPB=$cpb"
    fi
    PHASE_TOTAL=$((PHASE_TOTAL + 1))
    report PASS "Async RX phases" "CPB=$cpb; 36 good frames, 9 bad stops"
done
report PASS "Async configurations" "$PHASE_TOTAL / 4"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    report PASS "Git working tree" "Clean"
else
    report WARN "Git working tree" "Changes detected; no cleanup performed"
fi
report INFO "Coverage limits" "Scenario-hit counters only; no toggle/FSM/UCIS or CDC/formal signoff"
report INFO "Detailed log" "$LOG"
echo "===== END ASIC STAGE 1C ====="

#!/usr/bin/env bash
# ASIC Stage 1B — extended functional UART simulation (candidate regression).
# Safe fast-forward of clean Linux checkout. No source edits; outputs to G: Temp.
# Does not represent formal proof, coverage closure, CDC or physical signoff.
set -Eeuo pipefail

ROOT="/mnt/g/C-Drive-Backup-PreReset/Temp"
REPO="$HOME/projects/rtl-dv-lab"
echo "===== ASIC STAGE 1B: UART EXTENDED VERIFICATION ====="
if [[ ! -d "$ROOT" ]]; then
    echo "FAIL | G: Temp not mounted; no changes made"
    exit 1
fi
LOG="$ROOT/ASIC-Stage1B-UART-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
fail() {
    printf 'FAIL | %s\n' "$1"
    printf 'FAIL | %s\n' "$1" >> "$LOG"
    echo "===== COMPACT ERROR DIAGNOSTICS ====="
    grep -Ei 'UART_STRESS_FAIL|FATAL|error:|^%Warning|^%Error|syntax error|warning:|failed' "$LOG" | tail -n 12 || true
    echo "===== END ERROR DIAGNOSTICS ====="
    echo "INFO | Detailed log: $LOG"
    exit 1
}
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
[[ "$(id -un)" == "vaish" && "$(id -u)" != "0" ]] || fail "Run as non-root Ubuntu user vaish"
[[ -d "$REPO/.git" ]] || fail "Expected rtl-dv-lab checkout missing"
for tool in git iverilog vvp; do
    command -v "$tool" >/dev/null 2>&1 || fail "Missing executable: $tool"
done
[[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Checkout not on main branch"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] || fail "Unexpected origin"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "Checkout has local changes; refusing update"
report PASS "Checkout preflight" "Clean main, expected origin"
if ! git -C "$REPO" fetch origin main >> "$LOG" 2>&1; then
    fail "Git fetch failed"
fi
if ! git -C "$REPO" merge-base --is-ancestor HEAD origin/main; then
    fail "Local branch diverged; refusing merge"
fi
if ! git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1; then
    fail "Fast-forward failed"
fi
head="$(git -C "$REPO" rev-parse --short=12 HEAD)"
report PASS "Git fast-forward" "$head"
DESIGN="$REPO/asic_tapeout"
for file in rtl/uart_tx.sv rtl/uart_rx.sv rtl/uart_core.sv tb/tb_uart_stress.sv; do
    [[ -f "$DESIGN/$file" ]] || fail "Missing UART test input: $file"
done
WORK="$(mktemp -d "$ROOT/ASIC-Stage1B-UART.XXXXXXXX")"
cd "$WORK"
report INFO "Workspace" "$WORK"
report INFO "Test scope" "Continuous frames, malformed stop, long break, mid-RX reset, busy TX, concurrent TX/RX"
TOTAL=0
for cpb in 8 9 16 32; do
    if ! iverilog -g2012 -s tb_uart_stress -Ptb_uart_stress.CPB="$cpb" \
        -o "$WORK/stress_$cpb.vvp" \
        "$DESIGN/rtl/uart_tx.sv" "$DESIGN/rtl/uart_rx.sv" \
        "$DESIGN/rtl/uart_core.sv" "$DESIGN/tb/tb_uart_stress.sv" >> "$LOG" 2>&1; then
        fail "Icarus compile failed at CPB=$cpb"
    fi
    for seed in 20261116 20261117; do
        runlog="$WORK/stress_$cpb-$seed.log"
        if ! vvp "$WORK/stress_$cpb.vvp" "+SEED=$seed" > "$runlog" 2>&1; then
            cat "$runlog" >> "$LOG"
            fail "UART extended RTL regression failed at CPB=$cpb seed=$seed"
        fi
        cat "$runlog" >> "$LOG"
        if ! grep -q "^UART_STRESS_PASS: CPB=$cpb SEED=$seed " "$runlog"; then
            fail "UART stress PASS marker missing CPB=$cpb seed=$seed"
        fi
        TOTAL=$((TOTAL + 1))
        report PASS "UART stress" "CPB=$cpb seed=$seed"
    done
done
report PASS "Extended simulations" "$TOTAL deterministic runs"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    report PASS "Git working tree" "Clean"
else
    report WARN "Git working tree" "Modified; no cleanup attempted"
fi
report INFO "Verification limits" "No exhaustive coverage, CDC signoff, formal closure, STA, PDK or GDS"
report INFO "Detailed log" "$LOG"
echo "===== END ASIC STAGE 1B ====="

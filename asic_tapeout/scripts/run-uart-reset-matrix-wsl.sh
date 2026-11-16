#!/usr/bin/env bash
# ASIC Stage 1D: revalidate Stage 1C after checker timescale fix, then
# UART 8N1 TX/RX start/data/stop reset-phase sweep and recovery.
# Only fast-forward a clean main checkout; write logs/build files to G: Temp.
set -Eeuo pipefail
ROOT="/mnt/g/C-Drive-Backup-PreReset/Temp"
REPO="$HOME/projects/rtl-dv-lab"
echo "===== ASIC STAGE 1D: UART RESET AND COVERAGE MATRIX ====="
if [[ ! -d "$ROOT" ]]; then
    echo "FAIL | G: Temp missing; no changes made"
    exit 1
fi
LOG="$ROOT/ASIC-Stage1D-UART-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
fail() {
    printf 'FAIL | %s\n' "$1"
    printf 'FAIL | %s\n' "$1" >> "$LOG"
    echo "===== COMPACT ERROR DETAILS ====="
    grep -Ei 'UART_RESET_FAIL|UART_ASSERT_FAIL|UART_ASYNC_FAIL|UART_STRESS_FAIL|FATAL|error:|syntax error|^%Warning|^%Error' "$LOG" | tail -n 12 || true
    echo "===== END ERROR DETAILS ====="
    echo "INFO | Detailed log: $LOG"
    exit 1
}
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
[[ "$(id -un)" == "vaish" && "$(id -u)" != "0" ]] || fail "Run as normal Ubuntu user vaish"
for tool in git iverilog vvp; do
    command -v "$tool" >/dev/null 2>&1 || fail "Executable missing: $tool"
done
[[ -d "$REPO/.git" ]] || fail "Expected rtl-dv-lab Linux clone missing"
[[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Expected main"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] || fail "Unexpected origin URL"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "Checkout has local changes; refusing source update"
report PASS "Git preflight" "Clean main, expected origin"
if ! git -C "$REPO" fetch origin main >> "$LOG" 2>&1; then
    fail "Git fetch failed"
fi
if ! git -C "$REPO" merge-base --is-ancestor HEAD origin/main; then
    fail "Branch diverged; no merge attempted"
fi
if ! git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1; then
    fail "Git fast-forward failed"
fi
report PASS "Git fast-forward" "$(git -C "$REPO" rev-parse --short=12 HEAD)"
D="$REPO/asic_tapeout"
for file in rtl/uart_tx.sv rtl/uart_rx.sv rtl/uart_core.sv \
    tb/uart_interface_checkers.sv tb/tb_uart_reset_matrix.sv \
    scripts/run-uart-assertions-phase-wsl.sh; do
    [[ -f "$D/$file" ]] || fail "Missing expected source $file"
done
WORK="$(mktemp -d "$ROOT/ASIC-Stage1D-UART.XXXXXXXX")"
cd "$WORK"
report INFO "Workspace" "$WORK"
report INFO "Revalidation" "Rerun Stage 1C after explicit 1ns checker timescale"
if ! bash "$D/scripts/run-uart-assertions-phase-wsl.sh" > "$WORK/stage1c-recheck.log" 2>&1; then
    cat "$WORK/stage1c-recheck.log" >> "$LOG"
    fail "Stage 1C revalidation failed; inspect compact diagnostics"
fi
cat "$WORK/stage1c-recheck.log" >> "$LOG"
if ! grep -Fqx 'PASS | Monitored stress configurations | 8 / 8' "$WORK/stage1c-recheck.log" ||
   ! grep -Fqx 'PASS | Async configurations | 4 / 4' "$WORK/stage1c-recheck.log"; then
    fail "Stage 1C revalidation missing required PASS markers"
fi
report PASS "Stage 1C revalidated" "8 monitored and 4 asynchronous configurations"

TOTAL=0
for cpb in 8 9 16 32; do
    if ! iverilog -g2012 -s tb_uart_reset_matrix -Ptb_uart_reset_matrix.CPB="$cpb" \
        -o "$WORK/reset_$cpb.vvp" \
        "$D/rtl/uart_tx.sv" "$D/rtl/uart_rx.sv" "$D/rtl/uart_core.sv" \
        "$D/tb/uart_interface_checkers.sv" "$D/tb/tb_uart_reset_matrix.sv" >> "$LOG" 2>&1; then
        fail "UART reset matrix compilation failed CPB=$cpb"
    fi
    if ! vvp "$WORK/reset_$cpb.vvp" > "$WORK/reset_$cpb.log" 2>&1; then
        cat "$WORK/reset_$cpb.log" >> "$LOG"
        fail "UART reset matrix failed CPB=$cpb"
    fi
    cat "$WORK/reset_$cpb.log" >> "$LOG"
    if ! grep -Fqx "UART_RESET_PASS: CPB=$cpb tx_reset_phases=10 rx_reset_phases=10 tx_recovered=10 rx_recovered=10" "$WORK/reset_$cpb.log"; then
        fail "UART reset coverage marker missing CPB=$cpb"
    fi
    TOTAL=$((TOTAL + 1))
    report PASS "UART reset phases" "CPB=$cpb; 10 TX + 10 RX phase bins; 20 recovery transfers"
done
report PASS "Reset test configurations" "$TOTAL / 4 (80 reset phase/configuration tuples)"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    report PASS "Git working tree" "Clean"
else
    report WARN "Git working tree" "Changes found; not removed"
fi
report INFO "Limitations" "Directed reset/phase hits only; CDC, formal, complete coverage and physical signoff open"
report INFO "Detailed log" "$LOG"
echo "===== END ASIC STAGE 1D ====="

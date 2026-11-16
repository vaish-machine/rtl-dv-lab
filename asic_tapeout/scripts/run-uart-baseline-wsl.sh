#!/usr/bin/env bash
# ASIC Stage 1A: fast-forward clean local checkout, test initial UART candidate.
# Tests are logged under G:\C-Drive-Backup-PreReset\Temp and do not
# add generated files to Git. Physical design is not attempted.
set -Eeuo pipefail

REPO="$HOME/projects/rtl-dv-lab"
LOGROOT="/mnt/g/C-Drive-Backup-PreReset/Temp"
echo "===== ASIC STAGE 1A: UART RTL BASELINE ====="
if [[ ! -d "$LOGROOT" ]]; then
    echo "FAIL | G: Temp directory unavailable; nothing changed"
    exit 1
fi
LOG="$LOGROOT/ASIC-Stage1A-UART-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
fail() {
    echo "FAIL | $1"
    echo "FAIL | $1" >> "$LOG"
    echo "INFO | Detailed log: $LOG"
    exit 1
}
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
show_errors() {
    echo "===== COMPACT ERROR DETAILS (from G: log) ====="
    # Capture Verilator diagnostics such as %Warning-WIDTH: and
    # %Error: as well as traditional compiler 'error:' messages.
    grep -Ei '^%Warning|^%Error|error:|syntax error|unable to bind|unknown module|no such file|warning:|sorry:|failed' "$LOG" | tail -n 16 || true
    echo "===== END ERROR DETAILS ====="
}
[[ "$(id -un)" == "vaish" && "$(id -u)" != "0" ]] || fail "Run as normal Ubuntu user vaish"
[[ -d "$REPO/.git" ]] || fail "Cloned rtl-dv-lab not found"
for tool in git iverilog vvp verilator yosys; do
    command -v "$tool" >/dev/null 2>&1 || fail "Missing required tool: $tool"
done
report PASS "Linux user" "$(id -un)"
report PASS "RTL toolchain" "Icarus, Verilator and Yosys found"
remote="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
[[ "$remote" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] || fail "Unexpected origin remote; not syncing source"
branch="$(git -C "$REPO" branch --show-current)"
[[ "$branch" == "main" ]] || fail "Expected main branch; not syncing source"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "Checkout has local edits; refusing to alter working tree"
report PASS "Checkout preflight" "main, clean, expected GitHub origin"

report INFO "Git fetch" "Fetching origin/main (no local changes overwritten)"
if ! git -C "$REPO" fetch origin main >> "$LOG" 2>&1; then
    fail "Fetch failed; review G: log"
fi
if ! git -C "$REPO" merge-base --is-ancestor HEAD origin/main; then
    fail "Local checkout is not an ancestor of origin/main; no merge attempted"
fi
if ! git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1; then
    fail "Fast-forward failed; review G: log"
fi
head="$(git -C "$REPO" rev-parse --short=12 HEAD)"
report PASS "Fast-forward HEAD" "$head"

DESIGN="$REPO/asic_tapeout"
for file in rtl/uart_tx.sv rtl/uart_rx.sv rtl/uart_core.sv tb/tb_uart_core.sv; do
    [[ -f "$DESIGN/$file" ]] || fail "UART file missing: $file"
done
WORK="$(mktemp -d "$LOGROOT/ASIC-Stage1A-UART.XXXXXXXX")"
report INFO "Test workspace" "$WORK"
cd "$WORK"  # Keep any tool side-effects off C: and outside the source repo.
# -P permits actual compilation/testing with two different bit periods.
for cpb in 16 8; do
    report INFO "Icarus verification" "Starting CPB=$cpb"
    if ! iverilog -g2012 -s tb_uart_core -Ptb_uart_core.CPB="$cpb" \
        -o "$WORK/uart_$cpb.vvp" \
        "$DESIGN/rtl/uart_tx.sv" "$DESIGN/rtl/uart_rx.sv" \
        "$DESIGN/rtl/uart_core.sv" "$DESIGN/tb/tb_uart_core.sv" >> "$LOG" 2>&1; then
        show_errors
        fail "Icarus compile failed for CPB=$cpb"
    fi
    if ! vvp "$WORK/uart_$cpb.vvp" > "$WORK/uart_$cpb.log" 2>&1; then
        cat "$WORK/uart_$cpb.log" >> "$LOG"
        fail "Icarus RTL regression failed for CPB=$cpb"
    fi
    cat "$WORK/uart_$cpb.log" >> "$LOG"
    if ! grep -q "UART_BASELINE_PASS: CPB=$cpb " "$WORK/uart_$cpb.log"; then
        fail "Icarus did not print expected PASS marker for CPB=$cpb"
    fi
    report PASS "UART regression" "CPB=$cpb self-checking testbench"
done

if ! verilator --lint-only --sv -Wall --top-module uart_core \
    "$DESIGN/rtl/uart_tx.sv" "$DESIGN/rtl/uart_rx.sv" \
    "$DESIGN/rtl/uart_core.sv" >> "$LOG" 2>&1; then
    show_errors
    fail "Verilator -Wall lint failed; inspect G: log"
fi
report PASS "Verilator lint" "UART core and submodules, -Wall"

if ! yosys -Q -T -p \
    "read_verilog -sv $DESIGN/rtl/uart_tx.sv $DESIGN/rtl/uart_rx.sv $DESIGN/rtl/uart_core.sv; hierarchy -check -top uart_core; synth -top uart_core; check -assert; stat" \
    >> "$LOG" 2>&1; then
    show_errors
    fail "Yosys RTL synthesis/check failed; inspect G: log"
fi
report PASS "Yosys generic synthesis" "UART core synthesized; no SKY130 mapping performed"

if [[ -n "$(git -C "$REPO" status --porcelain)" ]]; then
    report WARN "Git working tree" "Changes found; script did not clean or reset"
else
    report PASS "Git working tree" "Clean"
fi
report INFO "Verification scope" "Directed baseline only; randomized, CDC, formal, coverage and physical signoff pending"
report INFO "Detailed log" "$LOG"
echo "===== END ASIC STAGE 1A ====="

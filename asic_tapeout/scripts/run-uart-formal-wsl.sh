#!/usr/bin/env bash
# ASIC Stage 1E: initial bounded Yosys/Z3 formal safety checks.
# Only fast-forwards clean Git main; no RTL mutations, no additional packages.
# Outputs and counterexamples are saved under G:\C-Drive-Backup-PreReset\Temp.
# NOT exhaustive proof, CDC signoff, liveness, or physical verification.
set -Eeuo pipefail
ROOT="/mnt/g/C-Drive-Backup-PreReset/Temp"
REPO="$HOME/projects/rtl-dv-lab"
echo "===== ASIC STAGE 1E: BOUNDED UART FORMAL CHECKS ====="
if [[ ! -d "$ROOT" ]]; then
    echo "FAIL | G: Temp directory not mounted; stopped"
    exit 1
fi
LOG="$ROOT/ASIC-Stage1E-Formal-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
fail() {
    printf 'FAIL | %s\n' "$1"
    printf 'FAIL | %s\n' "$1" >> "$LOG"
    echo "===== COMPACT FORMAL ERRORS ====="
    grep -Ei 'assert failed|status: failed|status: unknown|error:|^%Error|^%Warning|syntax error|trace|unconstrained|unsupported' "$LOG" | tail -n 12 || true
    echo "===== END ERRORS ====="
    printf 'INFO | Full log: %s\n' "$LOG"
    exit 1
}
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
[[ "$(id -u)" != "0" && "$(id -un)" == "vaish" ]] || fail "Must run as non-root user vaish"
for bin in git yosys yosys-smtbmc z3 timeout; do
    command -v "$bin" >/dev/null 2>&1 || fail "Missing required tool $bin; inspect installed Yosys package (no install attempted)"
done
report PASS "Formal executables" "Yosys, yosys-smtbmc, Z3 present"
report INFO "Yosys version" "$(yosys -V)"
report INFO "SMT solver" "$(z3 -version)"
[[ -d "$REPO/.git" ]] || fail "Expected rtl-dv-lab clone missing"
[[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Git checkout must be on main"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] || fail "Unexpected Git origin"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "Checkout modified; stopped without overwriting"
report PASS "Git preflight" "Clean main and known origin"
if ! git -C "$REPO" fetch origin main >> "$LOG" 2>&1; then fail "Fetch failed"; fi
if ! git -C "$REPO" merge-base --is-ancestor HEAD origin/main; then fail "Branch diverged; no merge"; fi
if ! git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1; then fail "Fast-forward failed"; fi
COMMIT="$(git -C "$REPO" rev-parse --short=12 HEAD)"
report PASS "Git fast-forward" "$COMMIT"
D="$REPO/asic_tapeout"
for file in rtl/uart_tx.sv rtl/uart_rx.sv formal/uart_formal_safety.sv; do
    [[ -f "$D/$file" ]] || fail "Missing formal input: $file"
done
WORK="$(mktemp -d "$ROOT/ASIC-Stage1E-Formal.XXXXXXXX")"
cd "$WORK"
report INFO "Workspace" "$WORK"
report INFO "Scope" "Bounded reset/idle/handshake and RX pulse/data safety, arbitrary sampled inputs"
report INFO "Assumptions" "One sampled reset at time zero; single synchronous clock (no analog metastability)"
TOTAL=0
for top in uart_tx_formal uart_rx_formal; do
    for cpb in 8 16; do
        test_id="$top-$cpb"
        smt="$WORK/$test_id.smt2"
        if ! yosys -Q -T -p "read_verilog -formal -sv $D/rtl/uart_tx.sv $D/rtl/uart_rx.sv $D/formal/uart_formal_safety.sv; chparam -set CLKS_PER_BIT $cpb $top; prep -top $top; async2sync; dffunmap; write_smt2 -wires $smt" >> "$LOG" 2>&1; then
            fail "Yosys formal translation failed: $test_id"
        fi
        [[ -s "$smt" ]] || fail "SMT2 model empty: $test_id"
        result="$WORK/$test_id-bmc.log"
        if ! timeout 90 yosys-smtbmc -s z3 -t 32 --dump-vcd "$WORK/$test_id-counterexample.vcd" "$smt" > "$result" 2>&1; then
            cat "$result" >> "$LOG"
            fail "Bounded model checking failed or timed out: $test_id"
        fi
        cat "$result" >> "$LOG"
        if ! grep -q 'Status: PASSED' "$result"; then
            fail "Missing explicit solver PASS status: $test_id"
        fi
        TOTAL=$((TOTAL + 1))
        report PASS "Bounded safety" "$test_id, 32 time steps (not unbounded proof)"
    done
done
# Non-vacuity check: prove a TX handshake can actually be reached after reset.
COVER_ID="uart_tx_formal-8"
if ! timeout 90 yosys-smtbmc -s z3 -c -t 16 \
    "$WORK/$COVER_ID.smt2" > "$WORK/tx-cover.log" 2>&1; then
    cat "$WORK/tx-cover.log" >> "$LOG"
    fail "TX handshake reachability cover failed or timed out"
fi
cat "$WORK/tx-cover.log" >> "$LOG"
grep -q 'Status: PASSED' "$WORK/tx-cover.log" || fail "Reachability cover did not PASS"
report PASS "TX reachability cover" "A valid TX request can occur after initial reset"
report PASS "Bounded configurations" "$TOTAL / 4"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    report PASS "Git working tree" "Clean"
else
    report WARN "Git working tree" "Modified; no cleanup performed"
fi
report INFO "Proof limitations" "32-step BMC and reachable handshake only; not a whole-frame/unbounded/formal signoff"
report INFO "CDC limitation" "rx_i modeled as arbitrary sampled bits; no metastability, MTBF or physical constraints"
report INFO "Detailed log" "$LOG"
echo "===== END ASIC STAGE 1E ====="

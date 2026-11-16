#!/usr/bin/env bash
# Stage 3A: isolated G:-backed SKY UART wrapper Icarus/Yosys smoke, NOT submission.
set -Eeuo pipefail
ROOT="/mnt/g/C-Drive-Backup-PreReset"
TEMP="$ROOT/Temp"
REPO="/home/vaish/projects/rtl-dv-lab"
BASE="/home/vaish/DevTools/LibreLane/ttsky_uart_wrapper_smoke"
GOLD2C="/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
GOLD2F="/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
HASH2C="3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
HASH2F="d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
echo "===== ASIC STAGE 3A: TTSKY UART WRAPPER SIMULATION ====="
if [[ ! -d "$TEMP" ]]; then echo "FAIL | G: Temp missing"; exit 1; fi
LOG="$TEMP/ASIC-Stage3A-TTSKY-UART-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
WORK=""
say() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
fail() {
    say FAIL "$1" "$2"
    if [[ -n "$WORK" ]]; then
        for f in "$WORK/iverilog.log" "$WORK/vvp.log" "$WORK/yosys.log"; do
            if [[ -f "$f" ]]; then
                echo "INFO | Diagnostic tail: $f"
                tail -n 12 "$f" || true
            fi
        done
        echo "INFO | Preserved workspace: $WORK"
    fi
    echo "INFO | G: summary: $LOG"
    exit 1
}
check_gds() {
    local path="$1"
    local expected="$2"
    [[ -f "$path" && ! -L "$path" ]] ||
        fail "Preserved GDSII" "Original layout missing or symlink"
    local observed
    observed="$(sha256sum "$path" | awk '{print $1}')"
    [[ "$observed" == "$expected" ]] ||
        fail "Preserved GDSII" "Unexpected SHA256 mismatch: $observed"
}
[[ "$(id -un)" == "vaish" && "$(id -u)" != 0 ]] ||
    fail "Linux identity" "Expected non-root Ubuntu vaish"
for cmd in git python3 iverilog vvp yosys sha256sum awk df mktemp grep; do
    command -v "$cmd" >/dev/null 2>&1 ||
        fail "Prerequisite" "$cmd not installed"
done
[[ -d "$REPO/.git" ]] || fail "Git" "Expected source checkout missing"
[[ "$(git -C "$REPO" branch --show-current)" == "main" ]] ||
    fail "Git" "Expected main branch"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] ||
    fail "Git" "Unexpected origin"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] ||
    fail "Git" "Local edits detected; refusing changes"
say PASS "Git preflight" "Clean main, expected origin"
git -C "$REPO" fetch origin main >> "$LOG" 2>&1 ||
    fail "Git fetch" "Fetch failed"
git -C "$REPO" merge-base --is-ancestor HEAD origin/main ||
    fail "Git fast-forward" "Divergence detected; no merge attempted"
git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1 ||
    fail "Git fast-forward" "Fast-forward failed"
say PASS "Git fast-forward" "$(git -C "$REPO" rev-parse HEAD)"
check_gds "$GOLD2C" "$HASH2C"
check_gds "$GOLD2F" "$HASH2F"
say PASS "Existing Stage 2C/2F GDSII" "Both known SHA256 checks passed"
GFREE="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
[[ "$GFREE" =~ ^[0-9]+$ && "$GFREE" -ge 5242880 ]] ||
    fail "G: storage" "Less than 5 GiB free"
say PASS "G: storage" "$((GFREE/1048576)) GiB free"
SRC="$REPO/asic_tapeout"
TT="$SRC/shuttle/ttsky_candidate"
for file in "$SRC/rtl/uart_tx.sv" "$SRC/rtl/uart_rx.sv" \
    "$SRC/rtl/uart_core.sv" "$TT/src/tt_um_vaish_uart.v" \
    "$TT/test/tb_tt_um_vaish_uart.sv"; do
    [[ -f "$file" && ! -L "$file" ]] ||
        fail "Sources" "Missing $file"
done
python3 - "$TT/src/tt_um_vaish_uart.v" >>"$LOG" 2>&1 <<'PY' ||
    fail "Candidate pin map" "Wrapper header/mapping does not match expected"
from pathlib import Path
import sys
text=Path(sys.argv[1]).read_text(encoding="utf-8")
markers=[
    "module tt_um_vaish_uart",
    "input  wire [7:0] ui_in", "output wire [7:0] uo_out",
    "input  wire [7:0] uio_in", "output wire [7:0] uio_out",
    "output wire [7:0] uio_oe",
    "input  wire       ena", "input  wire       clk",
    "input  wire       rst_n", ".tx_valid         (uio_in[0])",
    ".rx_i             (uio_in[1])", ".tx_data          (ui_in)",
    "assign uo_out  = rx_data;", "assign uio_oe  = 8'b0011_1100;",
    "CLKS_PER_BIT(16)",
]
assert all(marker in text for marker in markers), "Unexpected TT UART pin-map"
print("PASS | Candidate wrapper static interface | TT 8+8+8, CPB=16")
PY
say PASS "Candidate pin preflight" "TT top interface and uio_oe=0x3C"
mkdir -p "$BASE"
WORK="$(mktemp -d "$BASE/run-XXXXXXXX")"
mkdir -p "$WORK/src" "$WORK/test"
cp "$SRC/rtl/uart_tx.sv" "$SRC/rtl/uart_rx.sv" "$SRC/rtl/uart_core.sv" "$WORK/src/"
cp "$TT/src/tt_um_vaish_uart.v" "$WORK/src/"
cp "$TT/test/tb_tt_um_vaish_uart.sv" "$WORK/test/"
( cd "$WORK"; sha256sum src/* test/* ) > "$WORK/source-sha256.txt"
say PASS "Isolated G:-backed workspace" "$WORK"
say INFO "Official template reference" "TinyTapeout/ttsky-verilog-template @ a42e6662fab316e93b4e26399e21d41664a460b7"
export TMPDIR="$WORK"
iverilog -g2012 -s tb_tt_um_vaish_uart -o "$WORK/wrapper.vvp" \
    "$WORK/src/uart_tx.sv" "$WORK/src/uart_rx.sv" "$WORK/src/uart_core.sv" \
    "$WORK/src/tt_um_vaish_uart.v" "$WORK/test/tb_tt_um_vaish_uart.sv" \
    >"$WORK/iverilog.log" 2>&1 ||
    fail "Icarus compile" "Verilog/SystemVerilog compile failed"
say PASS "Icarus compile" "Existing UART modules + TT wrapper"
vvp "$WORK/wrapper.vvp" > "$WORK/vvp.log" 2>&1 ||
    fail "Directed wrapper simulation" "Self-checking test failed"
grep -Fq "PASS | Stage 3A Tiny Tapeout UART mapping simulation | All checks passed" "$WORK/vvp.log" ||
    fail "Directed wrapper simulation" "Final expected PASS marker missing"
grep '^PASS |' "$WORK/vvp.log" | tee -a "$LOG" || true
say PASS "Directed TX/RX wrapper simulation" "0xA5 TX and 0x5A RX frames"
yosys -Q -T -p \
  "read_verilog -sv $WORK/src/uart_tx.sv $WORK/src/uart_rx.sv $WORK/src/uart_core.sv $WORK/src/tt_um_vaish_uart.v; hierarchy -check -top tt_um_vaish_uart; proc; opt; check -assert" \
    > "$WORK/yosys.log" 2>&1 ||
    fail "Yosys wrapper check" "Nonzero exit or unresolved structural errors"
say PASS "Yosys wrapper check" "Hierarchy, proc/opt, structural checks"
check_gds "$GOLD2C" "$HASH2C"
check_gds "$GOLD2F" "$HASH2F"
say PASS "Original GDSII preservation" "Both SHA256s unchanged"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    say PASS "Git working tree" "Clean; original RTL untouched"
else
    say WARN "Git working tree" "Unexpected local changes; no cleanup attempted"
fi
say INFO "Scope boundary" "Wrapper feasibility/simulation only; template CI, tile sizing and shuttle submission NOT performed"
say INFO "Detailed Icarus output" "$WORK/vvp.log"
say INFO "Yosys output" "$WORK/yosys.log"
say INFO "G: summary" "$LOG"
echo "===== END ASIC STAGE 3A ====="

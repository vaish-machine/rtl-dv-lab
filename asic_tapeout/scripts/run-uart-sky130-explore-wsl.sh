#!/usr/bin/env bash
# ASIC Stage 2C: first exploratory UART digital CORE RTL-to-GDSII run.
# Pinned LibreLane 3.0.17, sky130A/sky130_fd_sc_hd.
# NOT a pad ring, official shuttle wrapper, signoff, or tapeout.
set -Eeuo pipefail
ROOT="/mnt/g/C-Drive-Backup-PreReset"
LOGDIR="$ROOT/Temp"
REPO="$HOME/projects/rtl-dv-lab"
APP="$HOME/DevTools/LibreLane/3.0.17/librelane-devshell-x86_64.AppImage"
EXPECTED_SHA="c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c"
BASE="$HOME/DevTools/LibreLane/uart_sky130_explore"
FLOW_LOG=""
WORK=""
echo "===== ASIC STAGE 2C: FIRST UART SKY130 PHYSICAL FLOW ====="
if [[ ! -d "$LOGDIR" ]]; then
    echo "FAIL | G: Temp not available; stopped before modifying anything"
    exit 1
fi
LOG="$LOGDIR/ASIC-Stage2C-UART-PHY-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
fail() {
    report FAIL "$1" "$2"
    echo "===== COMPACT FAILURE DETAILS ====="
    if [[ -n "$FLOW_LOG" && -f "$FLOW_LOG" ]]; then
        grep -Ei 'error|critical|fatal|failed|traceback|violation|No such file|not found|exception' "$FLOW_LOG" | tail -n 16 || true
        echo "INFO | Last flow lines:"
        tail -n 12 "$FLOW_LOG" || true
    else
        grep -Ei 'error|critical|fatal|failed|traceback|not found|exception' "$LOG" | tail -n 12 || true
    fi
    echo "===== END FAILURE DETAILS ====="
    echo "INFO | Detailed summary: $LOG"
    if [[ -n "$WORK" ]]; then echo "INFO | Retained run workspace: $WORK"; fi
    exit 1
}
[[ "$(id -un)" == vaish && "$(id -u)" != 0 ]] ||
    fail "Linux user" "Expected non-root vaish"
[[ "$(uname -m)" == x86_64 ]] ||
    fail "Linux architecture" "Expected x86_64"
for tool in git sha256sum stat df awk timeout mktemp find python3; do
    command -v "$tool" >/dev/null 2>&1 ||
        fail "Required tool" "$tool not found"
done
[[ -f "$APP" && ! -L "$APP" ]] ||
    fail "LibreLane AppImage" "Expected Stage 2B verified binary absent"
[[ "$(stat -c %s "$APP")" == 1398049312 ]] ||
    fail "LibreLane AppImage" "Size mismatch"
[[ "$(sha256sum "$APP" | awk '{print $1}')" == "$EXPECTED_SHA" ]] ||
    fail "LibreLane AppImage" "SHA256 mismatch; never execute unverified binary"
report PASS "Verified LibreLane" "3.0.17 official AppImage SHA256 checked"
[[ -d "$REPO/.git" ]] ||
    fail "Git source" "Expected Ubuntu project clone missing"
[[ "$(git -C "$REPO" branch --show-current)" == main ]] ||
    fail "Git branch" "Expected main"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] ||
    fail "Git origin" "Unexpected remote"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] ||
    fail "Git checkout" "Local modifications found; refusing to modify"
report PASS "Git preflight" "Clean main, known remote"
if ! git -C "$REPO" fetch origin main >> "$LOG" 2>&1; then
    fail "Git fetch" "Failed; inspect G: log"
fi
if ! git -C "$REPO" merge-base --is-ancestor HEAD origin/main; then
    fail "Git branch" "Diverged; no merge attempted"
fi
if ! git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1; then
    fail "Git fast-forward" "Failed"
fi
COMMIT="$(git -C "$REPO" rev-parse HEAD)"
report PASS "Git fast-forward" "$COMMIT"
D="$REPO/asic_tapeout"
CFG="$D/physical/uart_sky130_explore/config.json"
PIN="$D/physical/uart_sky130_explore/pin_order.cfg"
for f in "$CFG" "$PIN" "$D/rtl/uart_tx.sv" "$D/rtl/uart_rx.sv" "$D/rtl/uart_core.sv"; do
    [[ -f "$f" && ! -L "$f" ]] || fail "Physical source" "Missing or symlink: $f"
done
python3 - "$CFG" <<'PY'
import json,sys
with open(sys.argv[1],encoding="utf-8") as file:
    c=json.load(file)
assert c["DESIGN_NAME"]=="uart_core", "wrong top"
assert c["CLOCK_PORT"]=="clk", "unexpected clock"
assert c["CLOCK_PERIOD"]==100, "clock is not the pinned exploratory 100 ns"
assert c["FP_SIZING"]=="absolute" and c["DIE_AREA"]==[0,0,250,250], "die area changed"
assert c["VERILOG_FILES"]==["dir::src/uart_tx.sv","dir::src/uart_rx.sv","dir::src/uart_core.sv"], "RTL list changed"
assert c["IO_PIN_ORDER_CFG"]=="dir::pin_order.cfg"
PY
report PASS "Exploratory config" "UART CPB=16, 100 ns clock, 250 x 250 um die"
# Preflight the pinned LibreLane 3.0.17 Odb.CustomIOPlacement grammar.
# #N/#S/#E/#W are directives, NOT normal # comment headers.
# Require every real top-level pin to be allocated once, and every pattern
# to match a pin. Catch syntax typos before expensive physical design steps.
if ! python3 - "$PIN" <<'PY'
import re
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
sides = {}
side = None
for line_no, line in enumerate(lines, 1):
    token = line.strip()
    if not token:
        continue
    if token in ("#N", "#S", "#E", "#W"):
        side = token[1:]
        if side in sides:
            raise ValueError(f"Duplicate side directive {token} at line {line_no}")
        sides[side] = []
    else:
        if side is None:
            raise ValueError(f"Pin order needs a side directive first (line {line_no}: {token})")
        if token.startswith("#"):
            raise ValueError(f"Unsupported # comment or directive at line {line_no}: {token}")
        if token.startswith("@") or token.startswith("$"):
            raise ValueError(f"Unexpected annotation/virtual pin at line {line_no}: {token}")
        re.compile(token)
        sides[side].append(token)
if set(sides) != set("NESW"):
    raise ValueError(f"Missing one of four sides: found {list(sides)}")
ports = ["clk", "rst_n", "tx_valid", "tx_ready", "tx_o", "rx_i",
         "rx_valid", "rx_framing_error"]
ports += [f"tx_data[{i}]" for i in range(8)]
ports += [f"rx_data[{i}]" for i in range(8)]
for p in ports:
    matches = [(side_name, pattern)
               for side_name, patterns in sides.items()
               for pattern in patterns if re.fullmatch(pattern, p)]
    if len(matches) != 1:
        raise ValueError(f"Top-level port {p} must match exactly once: {matches}")
for side_name, patterns in sides.items():
    for pattern in patterns:
        if not any(re.fullmatch(pattern, p) for p in ports):
            raise ValueError(f"Unmatched pattern on {side_name} side: {pattern}")
print(f"PASS | Pin order preflight | {len(sides)} sides, {len(ports)} ports uniquely assigned")
PY
then
    fail "Pin-order preflight" "Invalid LibreLane IO syntax or incomplete port mapping"
fi
report PASS "Pin-order syntax" "4 directives; 24 scalar core ports assigned once"
report INFO "Technology" "sky130A / sky130_fd_sc_hd (provisional)"
report INFO "Nominal UART baud" "10 MHz / 16 = 625000 (provisional)"
G_FREE_KB="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
[[ "$G_FREE_KB" =~ ^[0-9]+$ && "$G_FREE_KB" -ge 20971520 ]] ||
    fail "G: available space" "Less than 20 GiB or unreadable"
report PASS "G: available space" "$((G_FREE_KB / 1048576)) GiB free"
mkdir -p "$BASE" "$HOME/DevTools/LibreLane/pdks" "$HOME/DevTools/LibreLane/tmp"
WORK="$(mktemp -d "$BASE/uart-core-XXXXXXXX")"
mkdir -p "$WORK/src"
cp "$D/rtl/uart_tx.sv" "$D/rtl/uart_rx.sv" "$D/rtl/uart_core.sv" "$WORK/src/"
cp "$CFG" "$PIN" "$WORK/"
{
    echo "Exploratory UART physical flow, NOT release signoff"
    echo "Git HEAD: $COMMIT"
    echo "LibreLane 3.0.17 SHA256: $EXPECTED_SHA"
    echo "PDK sky130A; SCL sky130_fd_sc_hd"
    echo "Clock 100ns; default CLKS_PER_BIT 16; die 250 x 250 um"
    echo "SHA256 of staged inputs:"
    sha256sum "$WORK/config.json" "$WORK/pin_order.cfg" "$WORK"/src/*.sv
} > "$WORK/PROVENANCE.txt"
report PASS "Staged RTL" "Exact source copied; Git source unchanged"
report INFO "Run workspace" "$WORK"
export PDK_ROOT="$HOME/DevTools/LibreLane/pdks"
export TMPDIR="$HOME/DevTools/LibreLane/tmp"
export XDG_CACHE_HOME="$HOME/.cache"
export PYTHONIOENCODING=utf-8
cd "$WORK"
TAG="explore-$(date +%Y%m%d-%H%M%S)"
FLOW_LOG="$WORK/librelane-$TAG.log"
report INFO "Run tag" "$TAG"
report INFO "Flow" "LibreLane Classic, sky130A, hd library, 2 jobs"
report INFO "Full flow log" "$FLOW_LOG"
if ! timeout 10800 "$APP" librelane \
    --pdk-root "$PDK_ROOT" --pdk sky130A --scl sky130_fd_sc_hd \
    --flow Classic --jobs 2 --run-tag "$TAG" \
    "$WORK/config.json" > "$FLOW_LOG" 2>&1; then
    fail "LibreLane UART physical flow" "Nonzero exit or timeout; no signoff/GDS claim"
fi
report PASS "LibreLane flow process" "Exited 0, checking final GDS artifact"
RUNROOT="$WORK/runs/$TAG"
[[ -d "$RUNROOT" ]] ||
    fail "Output directory" "Expected run dir absent: $RUNROOT"
GDS=""
while IFS= read -r candidate; do
    if [[ -s "$candidate" ]]; then
        GDS="$candidate"
        break
    fi
done < <(find "$RUNROOT/final" -type f -name '*.gds' 2>/dev/null || true)
[[ -n "$GDS" && -s "$GDS" ]] ||
    fail "GDSII artifact" "No nonempty final GDSII in completed run"
GDS_SHA="$(sha256sum "$GDS" | awk '{print $1}')"
report PASS "Exploratory UART GDSII" "$GDS"
report INFO "GDSII SHA256" "$GDS_SHA"
report INFO "GDSII size" "$(stat -c %s "$GDS") bytes"
report INFO "Run outputs" "$RUNROOT"
report INFO "Signoff" "NOT claimed: audit STA, DRC, LVS, PDK, pad IO and shuttle integration"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    report PASS "Git working tree" "Clean"
else
    report WARN "Git working tree" "Modified; script did not clean/reset"
fi
report INFO "Detailed log" "$LOG"
echo "===== END ASIC STAGE 2C ====="

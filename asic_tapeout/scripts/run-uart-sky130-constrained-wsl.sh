#!/usr/bin/env bash
# ASIC Stage 2F: exploratory UART sky130A physical run with explicit, PROVISIONAL
# 10 MHz core clock, synchronous host IO budgets, async rx_i exception.
# Preserve all Stage 2C results; never replace known-good GDS or change RTL.
# Only fast-forward a clean main; run results and full logs on G:-backed WSL ext4.
set -Eeuo pipefail

HOST="/mnt/g/C-Drive-Backup-PreReset"
TEMP="$HOST/Temp"
REPO="$HOME/projects/rtl-dv-lab"
APP="$HOME/DevTools/LibreLane/3.0.17/librelane-devshell-x86_64.AppImage"
APP_SHA="c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c"
GOLD="/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
GOLD_SHA="3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
BASE="$HOME/DevTools/LibreLane/uart_sky130_constrained"
WORK=""
FLOW_LOG=""

echo "===== ASIC STAGE 2F: UART SKY130 EXPLICIT SDC FLOW ====="
if [[ ! -d "$TEMP" ]]; then
    echo "FAIL | G: Temp not mounted; no changes made"
    exit 1
fi
LOG="$TEMP/ASIC-Stage2F-UART-SDC-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
fail() {
    report FAIL "$1" "$2"
    echo "===== COMPACT FAILURE DETAILS ====="
    if [[ -n "$FLOW_LOG" && -f "$FLOW_LOG" ]]; then
        grep -Ei "ERROR|CRITICAL|FATAL|FAILED|Traceback|syntax error|SDC|exception|violation" "$FLOW_LOG" | tail -n 14 || true
        tail -n 10 "$FLOW_LOG" || true
    else
        grep -Ei "ERROR|CRITICAL|FATAL|FAILED|Traceback|syntax error|exception" "$LOG" | tail -n 12 || true
    fi
    echo "===== END FAILURE DETAILS ====="
    echo "INFO | Detailed G: log: $LOG"
    if [[ -n "$WORK" ]]; then echo "INFO | Preserved workspace: $WORK"; fi
    exit 1
}
[[ "$(id -un)" == vaish && "$(id -u)" != 0 ]] ||
    fail "Linux user" "Expected normal non-root vaish"
for tool in git sha256sum stat df awk timeout python3 mktemp grep; do
    command -v "$tool" >/dev/null 2>&1 ||
        fail "Prerequisite" "Missing $tool"
done
[[ -f "$GOLD" && ! -L "$GOLD" ]] ||
    fail "Stage 2C reference GDS" "Original file missing or symlink"
[[ "$(sha256sum "$GOLD" | awk '{print $1}')" == "$GOLD_SHA" ]] ||
    fail "Stage 2C reference GDS" "Original GDS SHA256 mismatch, stopped"
report PASS "Previous golden GDSII" "Unchanged reference; SHA256 verified"
[[ -f "$APP" && ! -L "$APP" ]] ||
    fail "LibreLane" "Official pinned AppImage missing"
[[ "$(stat -c %s "$APP")" == 1398049312 ]] ||
    fail "LibreLane" "Unexpected package size"
[[ "$(sha256sum "$APP" | awk '{print $1}')" == "$APP_SHA" ]] ||
    fail "LibreLane" "Official SHA256 mismatch"
report PASS "LibreLane" "Verified official 3.0.17 AppImage"

[[ -d "$REPO/.git" ]] ||
    fail "Git checkout" "Expected rtl-dv-lab missing"
[[ "$(git -C "$REPO" branch --show-current)" == main ]] ||
    fail "Git checkout" "Expected main branch"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] ||
    fail "Git checkout" "Unexpected origin"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] ||
    fail "Git checkout" "Local modifications detected; refusing update"
report PASS "Git preflight" "Clean main and expected origin"
if ! git -C "$REPO" fetch origin main >> "$LOG" 2>&1; then
    fail "Git fetch" "Fetch failed"
fi
if ! git -C "$REPO" merge-base --is-ancestor HEAD origin/main; then
    fail "Git checkout" "Diverged; no merge attempted"
fi
if ! git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1; then
    fail "Git checkout" "Fast-forward failed"
fi
COMMIT="$(git -C "$REPO" rev-parse HEAD)"
report PASS "Git fast-forward" "$COMMIT"
D="$REPO/asic_tapeout"
PHY="$D/physical/uart_sky130_explore"
SDC="$PHY/constraints/uart_10mhz_provisional.sdc"
CFG="$PHY/config.json"
PINS="$PHY/pin_order.cfg"
for source in "$SDC" "$CFG" "$PINS" "$D/rtl/uart_tx.sv" "$D/rtl/uart_rx.sv" "$D/rtl/uart_core.sv"; do
    [[ -f "$source" && ! -L "$source" ]] ||
        fail "Source preflight" "Missing or symlink: $source"
done
if ! python3 - "$SDC" "$CFG" "$PINS" >> "$LOG" 2>&1 <<'PY'
import json,sys,re
from pathlib import Path
sdc=Path(sys.argv[1]).read_text(encoding="utf-8")
c=json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
pins=Path(sys.argv[3]).read_text(encoding="utf-8")
assert "create_clock -name uart_clk -period 100.0 [get_ports clk]" in sdc
assert "set_false_path -from [get_ports rx_i]" in sdc
assert sdc.count("set_false_path") == 1
assert "set_input_delay -max 10.0" in sdc
assert "set_output_delay -max 10.0" in sdc
assert "tx_data*" in sdc and "rx_data*" in sdc
assert c["CLOCK_PERIOD"] == 100 and c["DESIGN_NAME"]=="uart_core"
assert c["DIE_AREA"]==[0,0,250,250] and c["IO_PIN_ORDER_CFG"]=="dir::pin_order.cfg"
assert c["VERILOG_FILES"]==["dir::src/uart_tx.sv","dir::src/uart_rx.sv","dir::src/uart_core.sv"]
assert pins.splitlines()[0] == "#N"
assert all(pins.count(f"#{side}\n")==1 for side in "NSEW")
print("PASS | Physical input preflight | Original config, pins and provisional SDC consistent")
PY
then
    fail "Physical SDC preflight" "Source SDC/config/pins inconsistent; no flow run"
fi
report PASS "Provisional timing constraints" "100 ns clock; 0..10 ns synchronous IO budgets; async rx_i source false-path only"
report INFO "Constraint limitations" "Assumed input/output delays and loads; NOT signoff or fixed host interface"
G_FREE="$(df -Pk "$HOST" | awk 'NR==2 {print $4}')"
[[ "$G_FREE" =~ ^[0-9]+$ && "$G_FREE" -ge 15728640 ]] ||
    fail "G: storage" "Less than 15 GiB or free space unknown"
report PASS "G: available space" "$((G_FREE / 1048576)) GiB free"

mkdir -p "$BASE" "$HOME/DevTools/LibreLane/tmp" "$HOME/DevTools/LibreLane/pdks"
WORK="$(mktemp -d "$BASE/uart-core-sdc-XXXXXXXX")"
mkdir -p "$WORK/src"
cp "$D/rtl/uart_tx.sv" "$D/rtl/uart_rx.sv" "$D/rtl/uart_core.sv" "$WORK/src/"
cp "$PINS" "$WORK/pin_order.cfg"
cp "$SDC" "$WORK/src/uart_10mhz_provisional.sdc"
# Original exploratory config left unchanged. Add SDCs only inside the new
# unique G:-backed workspace. Both files intentionally use same provisional
# budgets until real wrapper clocks/delays are specified.
python3 - "$CFG" "$WORK/config.json" <<'PY'
import json,sys
from pathlib import Path
c=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
c["PNR_SDC_FILE"]="dir::src/uart_10mhz_provisional.sdc"
c["SIGNOFF_SDC_FILE"]="dir::src/uart_10mhz_provisional.sdc"
Path(sys.argv[2]).write_text(json.dumps(c,indent=2)+"\n",encoding="utf-8")
PY
{
    echo "UART SKY130 provisional SDC implementation; no signoff claimed"
    echo "Git HEAD: $COMMIT"
    echo "Prior GDS SHA256: $GOLD_SHA"
    echo "LibreLane AppImage SHA256: $APP_SHA"
    echo "PDK: sky130A; SCL: sky130_fd_sc_hd"
    echo "Clock=100 ns; TX synchronous IO 0..10 ns; RX external asynchronous"
    sha256sum "$WORK/config.json" "$WORK/pin_order.cfg" "$WORK"/src/*
} > "$WORK/PROVENANCE.txt"
report PASS "Staged inputs" "New isolated SDC run; original Stage 2C workspace preserved"
report INFO "Run workspace" "$WORK"

export PDK_ROOT="$HOME/DevTools/LibreLane/pdks"
export TMPDIR="$HOME/DevTools/LibreLane/tmp"
export XDG_CACHE_HOME="$HOME/.cache"
export PYTHONIOENCODING=utf-8
cd "$WORK"
TAG="sdc-explore-$(date +%Y%m%d-%H%M%S)"
FLOW_LOG="$WORK/librelane-$TAG.log"
report INFO "Physical flow" "LibreLane Classic sky130A / sky130_fd_sc_hd; 2 jobs; explicit PNR+signoff SDC"
report INFO "Full LibreLane log" "$FLOW_LOG"
if ! timeout 10800 "$APP" librelane \
    --pdk-root "$PDK_ROOT" --pdk sky130A --scl sky130_fd_sc_hd \
    --flow Classic --jobs 2 --run-tag "$TAG" "$WORK/config.json" \
    > "$FLOW_LOG" 2>&1; then
    fail "Constrained LibreLane flow" "Nonzero exit or timeout; inspect G: log"
fi
RUN="$WORK/runs/$TAG"
GDS="$RUN/final/gds/uart_core.gds"
METRICS="$RUN/final/metrics.json"
[[ -s "$GDS" && -f "$METRICS" ]] ||
    fail "Constrained flow outputs" "Expected nonempty GDSII and final metrics JSON absent"
if grep -Fq "'PNR_SDC_FILE' is not defined" "$FLOW_LOG" ||
   grep -Fq "'SIGNOFF_SDC_FILE' is not defined" "$FLOW_LOG"; then
    fail "Explicit timing SDC" "Unexpected generic fallback warning despite pinned SDC"
fi
report PASS "Constrained flow completion" "Full Classic process exited 0 with explicit PNR/signoff SDC"
report PASS "Constrained UART GDSII" "$GDS ($(stat -c %s "$GDS") bytes)"
report INFO "New GDSII SHA256" "$(sha256sum "$GDS" | awk '{print $1}')"
report INFO "Final metrics" "$METRICS"

# Non-failing audit of critical final metric counters. In this experimental
# phase, any unresolved counters remain REVIEW, not a signoff PASS.
python3 - "$METRICS" <<'PY' | tee -a "$LOG"
import json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for k in ["route__drc_errors","magic__drc_error__count","klayout__drc_error__count",
          "design__lvs_error__count","timing__setup_vio__count",
          "timing__hold_vio__count","timing__setup__wns","timing__hold__wns",
          "design__instance__count","design__instance__area",
          "design__core__area","power__total"]:
    if k in d:
        v=d[k]
        state="REVIEW" if (k.endswith("count") or "drc_errors" in k or "error__count" in k) and isinstance(v,(int,float)) and v>0 else "METRIC"
        print(f"{state} | {k} | {v}")
    else:
        matching={key:value for key,value in d.items() if key.startswith(k+"__")}
        if matching:
            vals=list(matching.values())
            print(f"INFO | {k} | {len(vals)} corner/class keys; exact values in metrics.json")
        else:
            print(f"MISSING | {k} | Not present in final metrics")
print("INFO | Timing limitation | PNR and SIGNOFF SDC use same provisional budget; NOT a real timing signoff")
PY

[[ "$(sha256sum "$GOLD" | awk '{print $1}')" == "$GOLD_SHA" ]] ||
    fail "Original Stage 2C GDS" "Reference changed unexpectedly"
report PASS "Original Stage 2C GDS" "Hash unchanged"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    report PASS "Git working tree" "Clean"
else
    report WARN "Git working tree" "Unexpected modifications detected; no reset or cleanup"
fi
report INFO "Review status" "Explicit provisional timing completed; actual clock/IO/wrapper, CDC and shuttle signoff OPEN"
report INFO "Detailed G: log" "$LOG"
report INFO "Constrained run outputs" "$RUN"
echo "===== END ASIC STAGE 2F ====="

#!/usr/bin/env bash
# Stage 3E: TT SKY130 3x2 footprint-aligned local exploratory RTL-to-GDSII.
# Uses pinned TT support-tools geometry and current TT source, local LibreLane 3.0.17.
# NOT the TT GitHub Actions GDS/precheck workflow; NOT slot allocation/signoff.
# Copy all inputs into a new native G:-backed Ubuntu WSL workspace.
set -Eeuo pipefail
HOST="/mnt/g/C-Drive-Backup-PreReset"
TEMP="$HOST/Temp"
REPO="/home/vaish/projects/rtl-dv-lab"
BASE="/home/vaish/DevTools/LibreLane/ttsky_sky130_3x2_trial"
SOURCE="/home/vaish/DevTools/LibreLane/ttsky_official_template_cocotb/run-i1DErq6p/template"
TT_URL="https://github.com/TinyTapeout/tt-support-tools.git"
TT_REV="9d13ff3e3e6202090740110438c6a10c1d62ca0f"
TEMPLATE_REV="a42e6662fab316e93b4e26399e21d41664a460b7"
APP="/home/vaish/DevTools/LibreLane/3.0.17/librelane-devshell-x86_64.AppImage"
APP_SHA="c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c"
PDK_ROOT="/home/vaish/DevTools/LibreLane/pdks"
ORIG2C="/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
ORIG2F="/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
HASH2C="3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
HASH2F="d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
SDC="/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc"
SDCSHA="a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4"
WORK=""
FLOW_LOG=""
echo "===== ASIC STAGE 3E: TTSKY 3X2 EXPERIMENTAL HARDENING ====="
if [[ ! -d "$TEMP" ]]; then echo "FAIL | G: Temp missing"; exit 1; fi
LOG="$TEMP/ASIC-Stage3E-TTSKY-3x2-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
say() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >>"$LOG"
}
fail() {
    say FAIL "$1" "$2"
    if [[ -n "$WORK" ]]; then
        for f in "$WORK/prepare.log" "$WORK/tt-fetch.log" "$WORK/input-check.log"; do
            if [[ -s "$f" ]]; then
                echo "INFO | Diagnostic tail | $f"
                tail -n 12 "$f" || true
            fi
        done
        if [[ -s "$FLOW_LOG" ]]; then
            echo "INFO | Physical-flow diagnostic summary | $FLOW_LOG"
            grep -Ei 'critical|ERROR|FAILED|FATAL|Traceback|unroutable|congestion|timing violation|PDK' "$FLOW_LOG" | tail -n 14 || true
            tail -n 9 "$FLOW_LOG" || true
        fi
        say INFO "Preserved isolated workspace" "$WORK"
    fi
    say INFO "Full G: summary" "$LOG"
    exit 1
}
verify_sha() {
    local path="$1" wanted="$2" label="$3" seen
    [[ -f "$path" && ! -L "$path" ]] ||
        fail "$label" "Missing or symlink: $path"
    seen="$(sha256sum "$path" | awk '{print $1}')"
    [[ "$seen" == "$wanted" ]] ||
        fail "$label" "SHA256 changed: $seen"
}
[[ "$(id -un)" == "vaish" && "$(id -u)" != 0 ]] ||
    fail "WSL identity" "Expected non-root Ubuntu user vaish"
for bin in git python3 sha256sum awk df mktemp timeout cp grep stat; do
    command -v "$bin" >/dev/null 2>&1 ||
        fail "Prerequisite" "$bin missing"
done
[[ -d "$REPO/.git" ]] || fail "Source" "Expected rtl-dv-lab checkout absent"
[[ "$(git -C "$REPO" branch --show-current)" == main ]] ||
    fail "Source" "Expected main"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] ||
    fail "Source" "Unexpected Git origin"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] ||
    fail "Source" "Local changes detected; refusing merge"
git -C "$REPO" fetch origin main >>"$LOG" 2>&1 ||
    fail "Source fetch" "Origin/main fetch failed"
git -C "$REPO" merge-base --is-ancestor HEAD origin/main ||
    fail "Source" "History diverged; no merge attempted"
git -C "$REPO" merge --ff-only origin/main >>"$LOG" 2>&1 ||
    fail "Source" "Fast-forward failed"
say PASS "Source revision" "$(git -C "$REPO" rev-parse HEAD)"
verify_sha "$ORIG2C" "$HASH2C" "Original Stage 2C GDS"
verify_sha "$ORIG2F" "$HASH2F" "Original Stage 2F GDS"
verify_sha "$SDC" "$SDCSHA" "Original Stage 2F SDC"
verify_sha "$APP" "$APP_SHA" "LibreLane 3.0.17 AppImage"
say PASS "Preserved inputs/tool" "Stage2C/2F GDS, SDC, LibreLane AppImage SHA256 verified"
[[ -d "$PDK_ROOT/sky130A" ]] ||
    fail "PDK" "SKY130A PDK missing under G:-backed WSL tools"
[[ -d "$SOURCE/.git" && -f "$SOURCE/test/results.xml" ]] ||
    fail "Stage 3C" "Known passing isolated official template not found"
[[ "$(git -C "$SOURCE" rev-parse HEAD)" == "$TEMPLATE_REV" ]] ||
    fail "Stage 3C" "Official template commit changed"
FREE="$(df -Pk "$HOST" | awk 'NR==2 {print $4}')"
[[ "$FREE" =~ ^[0-9]+$ && "$FREE" -ge 15728640 ]] ||
    fail "G: available storage" "Less than 15 GiB; refuse full physical flow"
say PASS "G: free space" "$((FREE/1048576)) GiB"
mkdir -p "$BASE"
WORK="$(mktemp -d "$BASE/run-XXXXXXXX")"
mkdir -p "$WORK/tmp" "$WORK/cache"
export TMPDIR="$WORK/tmp"
export XDG_CACHE_HOME="$WORK/cache"
export PYTHONNOUSERSITE=1
export PYTHONIOENCODING=utf-8
export PDK_ROOT
cp -a "$SOURCE" "$WORK/template" >"$WORK/prepare.log" 2>&1 ||
    fail "Staging" "Unable to copy successful Stage3C official template"
say PASS "New isolated TT trial workspace" "$WORK/template"
git clone -q "$TT_URL" "$WORK/template/tt" >"$WORK/tt-fetch.log" 2>&1 ||
    fail "TT official support-tools" "Repository clone failed"
git -C "$WORK/template/tt" checkout --detach --quiet "$TT_REV" >>"$WORK/tt-fetch.log" 2>&1 ||
    fail "TT official support-tools" "Pinned commit checkout failed"
[[ "$(git -C "$WORK/template/tt" rev-parse HEAD)" == "$TT_REV" ]] ||
    fail "TT official support-tools" "Unexpected ref"
say PASS "Pinned TT support tools" "$TT_REV"

# Reconstruct the exact *configuration recipe* from pinned tt-support-tools
# project.py:create_user_config + merge, using standard Python json (no global pip).
# This is provider-config-aligned locally, NOT an execution of the TT GitHub Action.
if ! python3 - "$WORK/template" "$REPO" <<'PY' >"$WORK/input-check.log" 2>&1
from pathlib import Path
import hashlib, json, re, sys
import xml.etree.ElementTree as ET
base,repo=map(Path,sys.argv[1:])
info=(base/"info.yaml").read_text(encoding="utf-8")
assert 'top_module: "tt_um_vaish_uart"' in info
assert 'tiles: "1x1"' in info and "PLACEHOLDER" in info
assert (base/"test/results.xml").exists()
xml=ET.parse(base/"test/results.xml").getroot()
cases=xml.findall(".//testcase")
assert cases and not any(t.find("failure") is not None or t.find("error") is not None or t.find("skipped") is not None for t in cases)
sources=["tt_um_vaish_uart.v","uart_core.sv","uart_tx.sv","uart_rx.sv"]
declared=re.findall(r'(?m)^    - "([^"]+)"\s*$',info)
assert len(declared)==4 and set(declared)==set(sources)
for name in sources:
    copied=base/"src"/name
    original=repo/"asic_tapeout"/("shuttle/ttsky_candidate/src" if name=="tt_um_vaish_uart.v" else "rtl")/name
    assert copied.is_file() and original.is_file() and copied.read_bytes()==original.read_bytes(),name
info=info.replace('tiles: "1x1"','tiles: "3x2"')
assert 'tiles: "3x2"' in info and 'tiles: "1x1"' not in info
(base/"info.yaml").write_text(info,encoding="utf-8")
tt=base/"tt"
tiles=(tt/"tech/sky130A/tile_sizes.yaml").read_text(encoding="utf-8")
assert re.search(r'^3x2: "0 0 508\.76 225\.76"$',tiles,re.M), "Provider tile size changed"
deffile=tt/"tech/sky130A/def/tt_block_3x2_pg.def"
deftext=deffile.read_text(encoding="utf-8")
assert "UNITS DISTANCE MICRONS 1000 ;" in deftext
assert "DIEAREA ( 0 0 ) ( 508760 225760 ) ;" in deftext
assert "PINS 43 ;" in deftext
cfgfile=base/"src/config.json"
original_cfg=json.loads(cfgfile.read_text(encoding="utf-8"))
assert original_cfg["FP_SIZING"]=="absolute"
assert original_cfg["CLOCK_PORT"]=="clk"
# Only in the isolated template copy: explicitly choose an exploratory
# 100ns period consistent with the historical 10MHz educational budget.
original_cfg["CLOCK_PERIOD"]=100
cfgfile.write_text(json.dumps(original_cfg,indent=2)+"\n",encoding="utf-8")
user_config={
    "DESIGN_NAME":"tt_um_vaish_uart",
    "VERILOG_FILES":["dir::"+name for name in declared],
    "DIE_AREA":"0 0 508.76 225.76",
    "FP_DEF_TEMPLATE":"dir::../tt/tech/sky130A/def/tt_block_3x2_pg.def",
    "VDD_PIN":"VPWR","GND_PIN":"VGND",
    "RT_MAX_LAYER":"met4",
}
merged=dict(original_cfg)
merged.update(user_config)
for key,val in user_config.items():
    assert merged[key]==val
(base/"src/user_config.json").write_text(json.dumps(user_config,indent=2)+"\n",encoding="utf-8")
(base/"src/config_merged.json").write_text(json.dumps(merged,indent=2)+"\n",encoding="utf-8")
manifest={
    "scope":"Local TT provider-configuration-recipe 3x2 trial, NOT TT Action",
    "support_tools_sha":"9d13ff3e3e6202090740110438c6a10c1d62ca0f",
    "template_sha":"a42e6662fab316e93b4e26399e21d41664a460b7",
    "tile":"3x2","die_area_um2":"114857.6576","clock_period_ns":100,
    "unverified_tile_choice":True,
    "provider_gds_precheck":False,
    "source_sha256":{p:hashlib.sha256((base/"src"/p).read_bytes()).hexdigest() for p in sources},
    "copied_cocotb_testcases":len(cases),
}
(base/"LOCAL_TRIAL_PROVENANCE.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
print("PASS | 3x2 source/layout inputs and pinned provider config recipe")
print("INFO | Official 3x2 SKY die rectangle 508.76 x 225.76 um")
print("INFO | Native G-backed local config_merged.json; 100ns EXPERIMENTAL clock")
PY
then
    fail "TT provider-style 3x2 config overlay" "Source/DEF/metadata/config validation failed"
fi
grep -Fq "PASS | 3x2 source/layout inputs" "$WORK/input-check.log" ||
    fail "TT input manifest" "Config preparation did not report completion"
say PASS "TT 3x2 configuration" "Exact provider DEF, four UART sources, provider config recipe, provisional 100ns clock"
say REVIEW "Tile choice" "3x2 exploration ONLY; no capacity certification or paid tile decision"
say INFO "Flow difference" "Local LibreLane AppImage v3.0.17, not provider TT Action's default v3.0.14"
FLOW_LOG="$WORK/physical-flow.log"
TAG="tt-3x2-$(date +%Y%m%d-%H%M%S)"
say INFO "Physical RTL-to-GDS flow" "LibreLane Classic SKY130 HD, pinned TT DEF, 2 jobs"
say INFO "Full physical log" "$FLOW_LOG"
# Maximum runtime cap; all logs and outputs are kept in a new G:-backed folder.
if ! (cd "$WORK/template" && timeout 10800 "$APP" librelane \
    --pdk-root "$PDK_ROOT" --pdk sky130A --scl sky130_fd_sc_hd \
    --flow Classic --jobs 2 --run-tag "$TAG" \
    "$WORK/template/src/config_merged.json") >"$FLOW_LOG" 2>&1; then
    fail "Experimental 3x2 physical hardening" "Local LibreLane exited nonzero or hit runtime limit"
fi
RUN="$WORK/template/runs/$TAG"
GDS="$RUN/final/gds/tt_um_vaish_uart.gds"
METRICS="$RUN/final/metrics.json"
[[ -s "$GDS" && -f "$METRICS" ]] ||
    fail "TT trial physical output" "Expected local GDSII and final metrics missing"
say PASS "TT-footprint 3x2 local GDS output" "$GDS ($(stat -c %s "$GDS") bytes)"
say INFO "New trial GDS SHA256" "$(sha256sum "$GDS" | awk '{print $1}')"
if ! python3 - "$METRICS" <<'PY' >"$WORK/metrics-summary.txt" 2>&1
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
assert isinstance(m,dict) and len(m)>100, "Missing expected final flow metrics"
print(f"PASS | Trial metrics | {len(m)} recorded values")
for key in ("design__instance__area","design__instance__count","design__core__area",
"route__drc_errors","magic__drc_error__count","klayout__drc_error__count",
"design__lvs_error__count","timing__setup_vio__count","timing__hold_vio__count",
"timing__setup__ws","timing__hold__ws","timing__setup__wns","timing__hold__wns"):
    v=m.get(key,"UNAVAILABLE")
    status="REVIEW" if v=="UNAVAILABLE" or ("drc" in key or "lvs_error" in key or "vio__count" in key) and isinstance(v,(int,float)) and v>0 else "METRIC"
    print(f"{status} | {key} | {v}")
print("INFO | Final metrics | physical trial only, not provider precheck or signoff")
PY
then
    fail "TT trial metrics" "Cannot parse local final flow metrics"
fi
cat "$WORK/metrics-summary.txt" | tee -a "$LOG"
verify_sha "$ORIG2C" "$HASH2C" "Stage 2C preserved GDS"
verify_sha "$ORIG2F" "$HASH2F" "Stage 2F preserved GDS"
verify_sha "$SDC" "$SDCSHA" "Stage 2F preserved SDC"
say PASS "Historic GDSII and SDC integrity" "Two GDSs + provisional SDC unchanged after physical run"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    say PASS "Original Git checkout" "Clean; no RTL edits"
else
    say REVIEW "Original Git checkout" "Unexpected changes present; did not clean or reset"
fi
say INFO "Output classification" "Local provider-footprint-aligned trial only; no official TT GDS Action/precheck or signoff"
say INFO "No transaction" "No user template repo, tile purchase, registration, shuttle slot or submission"
say INFO "Preserved new trial workspace" "$WORK"
say INFO "Summary log on G:" "$LOG"
echo "===== END ASIC STAGE 3E ====="

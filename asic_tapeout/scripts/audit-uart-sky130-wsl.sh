#!/usr/bin/env bash
# ASIC Stage 2D — READ-ONLY audit of the exact Stage 2C successful UART layout.
# No Git fetch, source edits, EDA re-execution, rerouting or changes to GDS.
# Writes a compact audit log and machine-readable metric evidence only to G: Temp.
set -Eeuo pipefail

ROOT="/mnt/g/C-Drive-Backup-PreReset"
TMP="$ROOT/Temp"
WORK="/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du"
TAG="explore-20261116-061728"
RUN="$WORK/runs/$TAG"
GDS="$RUN/final/gds/uart_core.gds"
FLOW_LOG="$WORK/librelane-$TAG.log"
EXPECTED_SHA="3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
EXPECTED_COMMIT="2ed57ff4cff277242cbcc397de0c2ee009c7eb1b"
echo "===== ASIC STAGE 2D: UART GDS AND PHYSICAL METRICS AUDIT ====="
if [[ ! -d "$TMP" ]]; then
    echo "FAIL | G: Temp directory unavailable; no files modified"
    exit 1
fi
LOG="$TMP/ASIC-Stage2D-UART-Audit-$(date +%Y%m%d-%H%M%S).log"
REPORT="$TMP/ASIC-Stage2D-UART-Metrics-$(date +%Y%m%d-%H%M%S).json"
DETAIL="$TMP/ASIC-Stage2D-UART-Parser-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
fail() {
    report FAIL "$1" "$2"
    echo "INFO | Detailed audit log: $LOG"
    exit 1
}

[[ "$(id -un)" == vaish && "$(id -u)" != 0 ]] ||
    fail "Linux identity" "Expected normal Ubuntu user vaish"
for tool in python3 sha256sum stat grep; do
    command -v "$tool" >/dev/null 2>&1 ||
        fail "Required tool" "$tool missing"
done
[[ -d "$RUN" && ! -L "$RUN" ]] ||
    fail "Exact Stage 2C run" "Missing retained run: $RUN"
[[ -f "$GDS" && ! -L "$GDS" ]] ||
    fail "Final GDSII" "Missing or symbolic link; no alternate GDS accepted"
[[ "$(stat -c %s "$GDS")" == 2053232 ]] ||
    fail "Final GDSII size" "Expected 2,053,232 bytes"
ACTUAL_SHA="$(sha256sum "$GDS" | cut -d ' ' -f 1)"
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] ||
    fail "Final GDSII SHA256" "Expected known Stage 2C hash; got $ACTUAL_SHA"
report PASS "Exact GDSII integrity" "2,053,232 bytes; SHA256 $ACTUAL_SHA"

PROVENANCE="$WORK/PROVENANCE.txt"
[[ -f "$PROVENANCE" && ! -L "$PROVENANCE" ]] ||
    fail "Source provenance" "PROVENANCE.txt is missing"
grep -Fq "Git HEAD: $EXPECTED_COMMIT" "$PROVENANCE" ||
    fail "Source provenance" "Run commit is not the expected Stage 2C commit"
report PASS "Source provenance" "$EXPECTED_COMMIT"

[[ -f "$FLOW_LOG" ]] ||
    fail "Original flow log" "Expected first-hand LibreLane log missing"
if grep -Fqi "Flow complete." "$FLOW_LOG"; then
    report PASS "LibreLane completion marker" "Found in retained run log"
else
    report WARN "LibreLane completion marker" "Marker not found; Stage 2C process exit was previously user-confirmed 0"
fi

if grep -Fq "'PNR_SDC_FILE' is not defined" "$FLOW_LOG" ||
   grep -Fq "'SIGNOFF_SDC_FILE' is not defined" "$FLOW_LOG"; then
    report REVIEW "Timing constraints" "Generic fallback SDC warnings detected; true clock/IO signoff OPEN"
else
    report INFO "Timing constraints" "No generic fallback marker matched; constraints still need independent audit"
fi
report INFO "Original full flow log" "$FLOW_LOG"
report INFO "Original outputs" "$RUN"

if ! python3 - "$RUN" "$REPORT" "$ACTUAL_SHA" <<'PY' > "$DETAIL" 2>&1
import csv
import json
import math
import sys
from pathlib import Path

run = Path(sys.argv[1])
out = Path(sys.argv[2])
gds_sha = sys.argv[3]
json_path = run / "final" / "metrics.json"
csv_path = run / "final" / "metrics.csv"
if json_path.is_file():
    metrics = json.loads(json_path.read_text(encoding="utf-8"))
    source = str(json_path)
elif csv_path.is_file():
    with csv_path.open(encoding="utf-8", newline="") as fh:
        metrics = {r["Metric"]: r["Value"] for r in csv.DictReader(fh)}
    source = str(csv_path)
else:
    raise RuntimeError("No final/metrics.json or final/metrics.csv found")
if not isinstance(metrics, dict) or not metrics:
    raise RuntimeError("Final metrics are not a nonempty mapping")

def numeric(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
    elif isinstance(value, str):
        try:
            v = float(value)
        except ValueError:
            return None
    else:
        return None
    return v if math.isfinite(v) else None

def matches(name):
    return [(k, metrics[k]) for k in sorted(metrics)
            if k == name or k.startswith(name + "__")]

def summarise(name):
    hits = matches(name)
    if not hits:
        return {"present": False}
    values = [(k, numeric(v)) for k, v in hits]
    usable = [(k, v) for k, v in values if v is not None]
    return {
        "present": True,
        "keys": [k for k, _ in hits],
        "values": {k: v for k, v in hits},
        "numeric_count": len(usable),
        "minimum": min((v for _, v in usable), default=None),
        "maximum": max((v for _, v in usable), default=None),
    }

groups = [
    ("Cells", "design__instance__count"),
    ("Cell area", "design__instance__area"),
    ("Core area", "design__core__area"),
    ("Utilization", "design__instance__utilization"),
    ("Setup WNS", "timing__setup__wns"),
    ("Setup TNS", "timing__setup__tns"),
    ("Hold WNS", "timing__hold__wns"),
    ("Setup violations", "timing__setup_vio__count"),
    ("Hold violations", "timing__hold_vio__count"),
    ("Route DRC errors", "route__drc_errors"),
    ("Magic DRC errors", "magic__drc_error__count"),
    ("LVS errors", "design__lvs_error__count"),
    ("LVS net mismatch", "design__lvs_net_difference__count"),
    ("LVS device mismatch", "design__lvs_device_difference__count"),
    ("Unmapped cells", "design__instance_unmapped__count"),
    ("Unconnected pins", "design__disconnected_pin__count"),
    ("Synthesis check errors", "synthesis__check_error__count"),
    ("Total power", "power__total"),
]
summary = {}
for label, prefix in groups:
    result = summarise(prefix)
    summary[prefix] = result
    if not result["present"]:
        print(f"MISSING | {label} | No final metric matching {prefix}")
        continue
    lo, hi, count = result["minimum"], result["maximum"], result["numeric_count"]
    if count:
        rounded = f"{lo:.6g}" if lo == hi else f"{lo:.6g} .. {hi:.6g}"
        print(f"METRIC | {label} | {rounded} (from {len(result['keys'])} key(s))")
    else:
        print(f"METRIC | {label} | Present, non-numeric (inspect JSON report)")
    if any(word in label.lower() for word in ("violations", "drc", "lvs", "errors", "unmapped", "unconnected", "synthesis")):
        if hi is not None and hi > 0:
            print(f"REVIEW | {label} | NONZERO value observed; must investigate before signoff")

# Evidence of each step is separately checked from raw metrics.
steps = [p.name for p in run.iterdir() if p.is_dir()]
for label, pattern in [
    ("Post-route STA", "openroad-stapostpnr"),
    ("Magic DRC", "magic-drc"),
    ("KLayout DRC", "klayout-drc"),
    ("Netgen LVS", "netgen-lvs"),
]:
    present = any(pattern in step for step in steps)
    print(f"{'FOUND' if present else 'MISSING'} | {label} step | {'Step directory exists' if present else 'Cannot confirm from step directories'}")

record = {
    "scope": "Stage 2D read-only metric inspection; not signoff",
    "run": str(run),
    "gds_sha256": gds_sha,
    "metrics_source": source,
    "total_metrics": len(metrics),
    "summary": summary,
    "step_directories": steps,
    "all_metrics": metrics,
}
out.write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
print(f"PASS | Final metrics parsed | {len(metrics)} keys from {source}")
print(f"INFO | Full machine-readable evidence | {out}")
print("INFO | Audit boundary | GDS authenticity and reported metrics only; NOT STA/DRC/LVS signoff")
PY
then
    tail -n 16 "$DETAIL" || true
    fail "Physical metric parsing" "Final metric evidence incomplete or unreadable; inspect log"
fi
cat "$DETAIL" | tee -a "$LOG"
report PASS "Stage 2D read-only extraction" "Exact GDS and retained metrics inspected"
report INFO "Detailed audit log" "$LOG"
report INFO "Metrics JSON report" "$REPORT"
echo "===== END ASIC STAGE 2D ====="

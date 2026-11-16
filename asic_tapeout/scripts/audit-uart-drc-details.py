#!/usr/bin/env python3
"""ASIC Stage 2E: read-only, exact-key audit of saved Stage 2C UART physical run.

Reads only the known successful run and its logs/metrics.
Writes only a short console summary and JSON + text evidence into G: Temp.
Does not alter Git, RTL, GDS, PDK, reports or kernel configuration.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from datetime import datetime

EXPECTED_GDS_SHA = "3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
EXPECTED_GDS_SIZE = 2053232
EXPECTED_COMMIT = "2ed57ff4cff277242cbcc397de0c2ee009c7eb1b"

BASE = Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du")
RUN = BASE / "runs" / "explore-20261116-061728"
GDS = RUN / "final" / "gds" / "uart_core.gds"
METRICS = RUN / "final" / "metrics.json"
FLOW_LOG = BASE / "librelane-explore-20261116-061728.log"
PROVENANCE = BASE / "PROVENANCE.txt"
TEMP = Path("/mnt/g/C-Drive-Backup-PreReset/Temp")

FAMILIES = {
    "Route DRC": "route__drc_errors",
    "Magic DRC": "magic__drc_error__count",
    "KLayout DRC": "klayout__drc_error__count",
    "LVS errors": "design__lvs_error__count",
    "LVS net diff": "design__lvs_net_difference__count",
    "LVS device diff": "design__lvs_device_difference__count",
    "LVS unmatched nets": "design__lvs_unmatched_net__count",
    "LVS unmatched pins": "design__lvs_unmatched_pin__count",
    "Setup WNS": "timing__setup__wns",
    "Hold WNS": "timing__hold__wns",
    "Setup TNS": "timing__setup__tns",
    "Hold TNS": "timing__hold__tns",
    "Setup violations": "timing__setup_vio__count",
    "Hold violations": "timing__hold_vio__count",
    "Instance count": "design__instance__count",
    "Instance area": "design__instance__area",
    "Core area": "design__core__area",
    "Die area": "design__die__area",
    "Utilization": "design__instance__utilization",
    "Total power": "power__total",
    "Unmapped cells": "design__instance_unmapped__count",
    "Disconnected pins": "design__disconnected_pin__count",
    "Synthesis errors": "synthesis__check_error__count",
}

STAGE_WORDS = {
    "Detailed routing": ("detailedrouting",),
    "Route DRC check": ("checker-trdrc", "trdrc"),
    "Magic DRC": ("magic-drc",),
    "KLayout DRC": ("klayout-drc",),
    "Netgen LVS": ("netgen-lvs",),
    "Post-route STA": ("stapostpnr",),
}

def emit(lines: list[str], level: str, what: str, detail: str) -> None:
    line = f"{level} | {what} | {detail}"
    print(line, flush=True)
    lines.append(line)

def safe_num(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        try:
            v = float(value)
            return v if math.isfinite(v) else None
        except ValueError:
            return None
    return None

def main() -> int:
    lines: list[str] = []
    print("===== ASIC STAGE 2E: UART ROUTE DRC AND FINAL REPORT DETAIL =====", flush=True)
    if os.geteuid() == 0 or os.environ.get("USER") != "vaish":
        emit(lines, "FAIL", "User", "Expected non-root Ubuntu user vaish")
        return 1
    if not TEMP.is_dir():
        emit(lines, "FAIL", "G: Temp", "Missing /mnt/g/.../Temp; no output written")
        return 1
    if not (GDS.is_file() and METRICS.is_file() and PROVENANCE.is_file() and FLOW_LOG.is_file()):
        emit(lines, "FAIL", "Exact original files", "Required GDS, metrics, provenance or flow log absent")
        return 1
    if GDS.stat().st_size != EXPECTED_GDS_SIZE:
        emit(lines, "FAIL", "GDS size", f"Unexpected {GDS.stat().st_size} bytes")
        return 1
    digest = hashlib.sha256()
    with GDS.open("rb") as stream:
        while block := stream.read(1 << 20):
            digest.update(block)
    if digest.hexdigest() != EXPECTED_GDS_SHA:
        emit(lines, "FAIL", "GDS SHA256", "Does not match preserved successful run")
        return 1
    emit(lines, "PASS", "Exact UART GDSII", f"{EXPECTED_GDS_SIZE} bytes, SHA256 verified")
    if f"Git HEAD: {EXPECTED_COMMIT}" not in PROVENANCE.read_text(encoding="utf-8"):
        emit(lines, "FAIL", "Run provenance", "Wrong source revision")
        return 1
    emit(lines, "PASS", "Run revision", EXPECTED_COMMIT)

    with METRICS.open(encoding="utf-8") as file:
        metrics = json.load(file)
    if not isinstance(metrics, dict) or not metrics:
        emit(lines, "FAIL", "Final metrics", "Expected a nonempty JSON mapping")
        return 1
    emit(lines, "PASS", "Saved final metrics", f"{len(metrics)} entries (unaltered)")

    entries: dict[str, dict] = {}
    for label, prefix in FAMILIES.items():
        exact = [(str(k), v) for k, v in metrics.items()
                 if k == prefix or str(k).startswith(prefix + "__")]
        numeric = [(k, safe_num(v)) for k, v in exact]
        usable = [(k, v) for k, v in numeric if v is not None]
        entries[label] = {
            "prefix": prefix,
            "key_values": {k: v for k, v in exact},
            "minimum": min((v for _, v in usable), default=None),
            "maximum": max((v for _, v in usable), default=None),
            "observations": len(exact),
            "nonzero": {k: v for k, v in usable if v != 0},
        }

    # Print ALL route DRC keys and values; these were previously aggregated
    # into a misleading 0..8 range by Stage 2D.
    route = entries["Route DRC"]
    if route["observations"] == 0:
        emit(lines, "MISSING", "Route DRC", "No saved route__drc_errors entries")
    else:
        for key, val in route["key_values"].items():
            emit(lines, "DRC_KEY", key, str(val))
        if route["nonzero"]:
            emit(lines, "REVIEW", "Routing DRC",
                 f"{len(route['nonzero'])} nonzero key(s); do NOT assume final clean")
        else:
            emit(lines, "INFO", "Routing DRC", "Saved values zero; final DRC report still requires review")

    for label in ("Magic DRC", "KLayout DRC", "LVS errors", "Setup violations", "Hold violations",
                  "Setup WNS", "Hold WNS", "Instance count", "Instance area", "Core area",
                  "Utilization", "Total power"):
        d = entries[label]
        if d["observations"] == 0:
            emit(lines, "MISSING", label, "No corresponding metrics")
            continue
        small = d["minimum"] == d["maximum"]
        value = str(d["maximum"]) if small else f"{d['minimum']} .. {d['maximum']}"
        emit(lines, "METRIC", label, f"{value} across {d['observations']} distinct key(s)")
        if label in ("Magic DRC", "KLayout DRC", "LVS errors", "Setup violations", "Hold violations") and d["nonzero"]:
            emit(lines, "REVIEW", label, "Nonzero metric(s); inspect exact keys in evidence JSON")

    # Give exact keys for the endpoint-relevant critical metrics, capped for
    # screen readability; all key/values are preserved in JSON.
    for label in ("Setup WNS", "Hold WNS", "Instance count", "Instance area"):
        d = entries[label]
        ordered = list(d["key_values"].items())
        for key, val in ordered[-4:]:
            emit(lines, "RAW_KEY", key, str(val))
        if len(ordered) > 4:
            emit(lines, "INFO", label, f"{len(ordered) - 4} additional exact entries in saved evidence")

    stage_dirs = [p for p in RUN.iterdir() if p.is_dir()]
    step_evidence: dict[str, list[dict]] = {}
    for label, probes in STAGE_WORDS.items():
        matching = [p for p in stage_dirs if any(probe in p.name.lower() for probe in probes)]
        step_evidence[label] = [
            {
                "directory": str(p),
                "logs": [str(q) for q in sorted(p.rglob("*.log"))[:8] if q.is_file()],
                "reports": [str(q) for q in sorted(p.rglob("*.rpt"))[:10] if q.is_file()],
            }
            for p in sorted(matching, key=lambda p: p.name)
        ]
        if matching:
            emit(lines, "FOUND", label, f"{len(matching)} step folder(s), report paths saved")
        else:
            emit(lines, "MISSING", label, "No matching step directory; not verified")

    flow_text = FLOW_LOG.read_text(encoding="utf-8", errors="replace")
    fallback = ("'PNR_SDC_FILE' is not defined" in flow_text or
                "'SIGNOFF_SDC_FILE' is not defined" in flow_text)
    emit(lines, "REVIEW" if fallback else "INFO", "SDC constraints",
         "Generic fallback detected; timing signoff OPEN" if fallback
         else "No fallback warning matched; independently review constraints")

    print("INFO | DRC interpretation | Stage-specific counts may include transient routing errors.", flush=True)
    print("INFO | Physical signoff | OPEN until detailed final DRC/LVS/STA constraints reviewed.", flush=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_json = TEMP / f"ASIC-Stage2E-UART-Detail-{stamp}.json"
    out_txt = TEMP / f"ASIC-Stage2E-UART-Detail-{stamp}.txt"
    record = {
        "scope": "READ ONLY; evidence extraction, NOT signoff",
        "source_run": str(RUN),
        "expected_git_head": EXPECTED_COMMIT,
        "gds_sha256": EXPECTED_GDS_SHA,
        "metrics_source": str(METRICS),
        "metric_families": entries,
        "step_evidence": step_evidence,
        "generic_fallback_sdc": fallback,
        "all_307_metrics": metrics,
    }
    out_json.write_text(json.dumps(record, indent=2, default=str, sort_keys=True) + "\n", encoding="utf-8")
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    emit(lines, "PASS", "Read-only Stage 2E extraction", "Completed; violations remain REVIEW")
    emit(lines, "INFO", "Full metric evidence", str(out_json))
    emit(lines, "INFO", "Compact audit text", str(out_txt))
    print("===== END ASIC STAGE 2E =====", flush=True)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"FAIL | Stage 2E detail inspection | {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)

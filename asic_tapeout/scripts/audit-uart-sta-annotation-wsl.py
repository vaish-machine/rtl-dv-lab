#!/usr/bin/env python3
r"""Stage 2H: read-only review of the exact Stage 2F post-route STA reports.

No EDA execution, Git operations, package installation, or edits to source,
layout, metrics, or PDK. Only final audit JSON/text is written under G:\Temp
(the actual G:\C-Drive-Backup-PreReset\Temp path).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import getpass
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HOST = Path("/mnt/g/C-Drive-Backup-PreReset")
TMP = HOST / "Temp"
BASE = Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x")
RUN = BASE / "runs/sdc-explore-20261116-074159"
GDS = RUN / "final/gds/uart_core.gds"
METRICS = RUN / "final/metrics.json"
CONFIG = RUN / "resolved.json"
SDC = BASE / "src/uart_10mhz_provisional.sdc"
ORIGINAL = Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
EXPECTED_GDS = "d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
EXPECTED_OLD = "3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
EXPECTED_SDC = "a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4"
EXPECTED_COMMIT = "712be2f718757d55f6aa7ab154d05f8d050bacac"

lines = []

def emit(label, item, detail):
    line = f"{label} | {item} | {detail}"
    print(line, flush=True)
    lines.append(line)

def digest_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while b := stream.read(1024 * 1024):
            h.update(b)
    return h.hexdigest()

def require_file(path, desc, expected_digest=None):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{desc} missing or symlink: {path}")
    if expected_digest is not None and digest_file(path) != expected_digest:
        raise RuntimeError(f"{desc} SHA256 does not match saved Stage 2F evidence")

def num(v):
    if isinstance(v, bool):
        return None
    try:
        n = float(v)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError, OverflowError):
        return None

def parse_unannotated(text):
    # Mirrors LibreLane 3.0.17 filter_unannotated.py: the report section
    # begins at report_parasitic_annotation -report_unannotated, ends at ===.
    report_lines = text.splitlines()
    start = next(
        (i for i, v in enumerate(report_lines)
         if v.strip() == "report_parasitic_annotation -report_unannotated"),
        None
    )
    if start is None:
        return {"found": False, "reported_driver_counts": {}, "names": [], "raw": []}
    end = next(
        (i for i in range(start + 1, len(report_lines))
         if re.fullmatch(r"={8,}", report_lines[i].strip())),
        min(len(report_lines), start + 320)
    )
    chunk = report_lines[start + 1:end]
    driver_counts = {}
    names = []
    for line in chunk:
        m = re.search(r"Found\s+(\d+)\s+((?:partially\s+)?unannotated)\s+drivers", line)
        if m:
            driver_counts[m.group(2)] = int(m.group(1))
        if re.match(r"^\s+\S", line):
            t = line.strip()
            if t and not t.startswith("Found ") and not t.startswith("#"):
                names.append(t)
    return {
        "found": True, "reported_driver_counts": driver_counts,
        "names": sorted(set(names)), "raw": chunk[:180]
    }

def inspect_reports(corner_dir):
    # Read existing STA reports only; never launch OpenROAD or synth tools.
    data = {}
    searched = 0
    no_paths = []
    timing_paths = []
    summary = []
    for p in sorted(corner_dir.rglob("*.rpt")):
        if not p.is_file():
            continue
        if p.stat().st_size > 8 * 1024 * 1024:
            summary.append({"file": str(p), "issue": "large (>8MiB); skipped path scan"})
            continue
        searched += 1
        contents = p.read_text(encoding="utf-8", errors="replace")
        count_start = len(re.findall(r"(?m)^\s*Startpoint:", contents))
        count_end = len(re.findall(r"(?m)^\s*Endpoint:", contents))
        nopath = len(re.findall(r"(?i)\bno paths found\b", contents))
        if count_start and count_end:
            timing_paths.append({"file": str(p), "startpoints": count_start, "endpoints": count_end})
        if nopath:
            no_paths.append({"file": str(p), "occurrences": nopath})
        summary.append({"file": str(p), "bytes": p.stat().st_size,
                        "startpoint_mentions": count_start,
                        "endpoint_mentions": count_end,
                        "no_paths_found": nopath})
    return {"reports_scanned": searched, "report_files": summary,
            "timing_path_examples": timing_paths[:12],
            "no_paths_found_files": no_paths[:16]}

def main():
    print("===== ASIC STAGE 2H: UART POST-ROUTE STA AND UNANNOTATED NET AUDIT =====", flush=True)
    if getpass.getuser() != "vaish" or __import__("os").geteuid() == 0:
        raise RuntimeError("Run with WSL Ubuntu as non-root user vaish")
    if not TMP.is_dir():
        raise RuntimeError("G: Temp not mounted; no output created")
    for item, desc, sha in [
        (GDS, "Stage 2F GDS", EXPECTED_GDS),
        (ORIGINAL, "Preserved Stage 2C GDS", EXPECTED_OLD),
        (SDC, "Stage 2F applied SDC", EXPECTED_SDC),
    ]:
        require_file(item, desc, sha)
        emit("PASS", desc, "SHA256 matches verified previous run")
    for path in [METRICS, CONFIG, BASE / "PROVENANCE.txt"]:
        require_file(path, path.name)
    provenance = (BASE / "PROVENANCE.txt").read_text(encoding="utf-8")
    if f"Git HEAD: {EXPECTED_COMMIT}" not in provenance:
        raise RuntimeError("Stage 2F run provenance commit mismatch")
    emit("PASS", "Stage 2F source commit", EXPECTED_COMMIT)
    metric = json.loads(METRICS.read_text(encoding="utf-8"))
    resolved = json.loads(CONFIG.read_text(encoding="utf-8"))
    if not isinstance(metric, dict) or not isinstance(resolved, dict):
        raise RuntimeError("Expected dictionary metrics and resolved configuration")
    for key in ("PNR_SDC_FILE", "SIGNOFF_SDC_FILE"):
        val = resolved.get(key)
        if not isinstance(val, str):
            raise RuntimeError(f"{key} unset or not path string")
        path = Path(val)
        if not path.is_absolute():
            path = BASE / path
        if path.resolve(strict=True) != SDC.resolve(strict=True):
            raise RuntimeError(f"{key} does not resolve to expected SDC: {val}")
    emit("PASS", "Resolved SDC", "PNR and signoff paths point to same pinned provisional SDC")
    emit("PASS", "Final metrics", f"{len(metric)} keys")
    for key in ("timing__unannotated_net__count", "timing__unannotated_net_filtered__count",
                "timing__setup__wns", "timing__hold__wns",
                "timing__setup_vio__count", "timing__hold_vio__count"):
        val = metric.get(key)
        emit("METRIC" if val is not None else "MISSING", key, str(val) if val is not None else "No unqualified final key")

    sta_steps = sorted(
        [p for p in RUN.iterdir() if p.is_dir() and "openroad-stapostpnr" in p.name.lower()],
        key=lambda p: p.name
    )
    if len(sta_steps) != 1:
        raise RuntimeError(f"Expected one post-PnR STA step; found {len(sta_steps)}")
    sta = sta_steps[0]
    emit("PASS", "Post-route STA step", sta.name)
    corners = sorted(p for p in sta.iterdir() if p.is_dir())
    if not corners:
        raise RuntimeError("No post-route STA corner folders found")
    all_names = defaultdict(list)
    audit = []
    reports_with_timing_paths = 0
    checked = 0
    for corner in corners:
        checks = corner / "checks.rpt"
        if not checks.is_file() or checks.is_symlink():
            emit("REVIEW", f"Corner {corner.name}", "checks.rpt missing; timing evidence incomplete")
            audit.append({"corner": corner.name, "checks_report_found": False})
            continue
        checked += 1
        report = parse_unannotated(checks.read_text(encoding="utf-8", errors="replace"))
        stat = inspect_reports(corner)
        if stat["timing_path_examples"]:
            reports_with_timing_paths += 1
        # Published metrics distinguish reported unannotated nets from actual
        # physical wires selected by the OpenDB filter.
        raw_key = f"timing__unannotated_net__count__corner:{corner.name}"
        filtered_key = f"timing__unannotated_net_filtered__count__corner:{corner.name}"
        raw_val = metric.get(raw_key)
        filtered_val = metric.get(filtered_key)
        for name in report["names"]:
            all_names[name].append(corner.name)
        count = len(report["names"])
        status = "REPORT" if report["found"] else "REVIEW"
        emit(status, f"STA corner {corner.name}",
             f"unannotated metric={raw_val}, filtered={filtered_val}, report names={count}; "
             f"timing-path report files={len(stat['timing_path_examples'])}")
        if stat["no_paths_found_files"]:
            emit("REVIEW", f"STA corner {corner.name}",
                 f"'{len(stat['no_paths_found_files'])}' report file(s) contain 'No paths found'")
        audit.append({
            "corner": corner.name,
            "checks_report_found": True,
            "unannotated": report,
            "raw_unannotated_metric": raw_val,
            "filtered_unannotated_metric": filtered_val,
            "raw_metric_key": raw_key,
            "filtered_metric_key": filtered_key,
            "path_report_evidence": stat,
            "filter_unannotated_log": str(corner / "filter_unannotated.log")
                    if (corner / "filter_unannotated.log").is_file() else None,
        })
    if not checked:
        raise RuntimeError("No checks.rpt files found in post-route STA corners")
    emit("INFO", "Post-route STA corners", f"{checked} with checks.rpt; {len(corners)} total")
    emit("INFO", "Timed path report evidence",
         f"{reports_with_timing_paths}/{checked} corners contain Startpoint/Endpoint mentions in *.rpt")
    emit("INFO", "Distinct reported unannotated names", str(len(all_names)))
    for name, seen in sorted(all_names.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:12]:
        emit("NET", name, f"reported in {len(seen)} corner(s): {', '.join(seen[:3])}")
    if len(all_names) > 12:
        emit("INFO", "Additional net names", f"{len(all_names)-12} names only in JSON evidence")
    if not all_names and metric.get("timing__unannotated_net__count", 0) != 0:
        emit("REVIEW", "Unannotated net identification",
             "Count nonzero but no names extracted; manual STA report inspection required")
    emit("INFO", "SDC and PVT limitations",
         "Timing closure NOT signed off; 100ns/10ns IO budgets, rx_i exception and loads provisional")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_out = TMP / f"ASIC-Stage2H-UART-STA-Details-{stamp}.json"
    txt_out = TMP / f"ASIC-Stage2H-UART-STA-Summary-{stamp}.txt"
    evidence = {
        "scope": "Read-only checks.rpt and OpenSTA reported-corner examination, not signoff",
        "run": str(RUN), "sta_step": str(sta),
        "gds_sha256": EXPECTED_GDS, "sdc_sha256": EXPECTED_SDC,
        "source_commit": EXPECTED_COMMIT,
        "unannotated_metric_keys": {k: v for k,v in metric.items()
                                    if k.startswith("timing__unannotated_net")},
        "setup_hold_metric_keys": {k: v for k,v in metric.items()
                                   if k.startswith("timing__setup__wns")
                                   or k.startswith("timing__hold__wns")
                                   or k.startswith("timing__setup_vio__count")
                                   or k.startswith("timing__hold_vio__count")},
        "unique_reported_names": dict(all_names),
        "corner_reports": audit,
        "resolved_sdc_paths": {k: resolved[k] for k in ("PNR_SDC_FILE","SIGNOFF_SDC_FILE")},
    }
    json_out.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str)+"\n",
                        encoding="utf-8")
    emit("PASS", "Stage 2H evidence extraction", "Completed; no design files changed")
    emit("INFO", "Full report JSON", str(json_out))
    emit("INFO", "Compact G: summary", str(txt_out))
    txt_out.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("===== END ASIC STAGE 2H =====",flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL | Stage 2H audit | {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)

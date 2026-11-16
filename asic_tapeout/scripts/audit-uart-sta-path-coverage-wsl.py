#!/usr/bin/env python3
r"""Stage 2I: read-only investigation of actual "No paths found" STA contexts.

Examines saved Stage 2F OpenSTA *.rpt/checks.rpt and filter_unannotated.log
from the nine post-route PVT corners. No Git/EDA execution or design changes.
Writes summaries and complete bounded evidence only to G:\C-Drive-Backup-PreReset\Temp.
"""
from __future__ import annotations
from datetime import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys

TEMP = Path("/mnt/g/C-Drive-Backup-PreReset/Temp")
BASE = Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x")
RUN = BASE / "runs/sdc-explore-20261116-074159"
GDS = RUN / "final/gds/uart_core.gds"
OLD = Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
SDC = BASE / "src/uart_10mhz_provisional.sdc"
EXPECTED_GDS = "d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
EXPECTED_OLD = "3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
EXPECTED_SDC = "a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4"
EXPECTED_REV = "712be2f718757d55f6aa7ab154d05f8d050bacac"
MAX_REPORT_SIZE = 8 * 1024 * 1024
MARKER = re.compile(r"(?i)\bno paths found\b")
UNANNOTATED = re.compile(r"(?i)(unannotated|report_parasitic_annotation)")
STARTPOINT = re.compile(r"(?m)^\s*Startpoint:\s*(.+)")
ENDPOINT = re.compile(r"(?m)^\s*Endpoint:\s*(.+)")
WARNING = re.compile(r"(?i)(unconstrained|not constrained|no clock|missing clock|unannotated|no paths found)")
logs = []

def emit(level, subject, detail):
    entry = f"{level} | {subject} | {detail}"
    print(entry, flush=True)
    logs.append(entry)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while b := stream.read(1024 * 1024):
            h.update(b)
    return h.hexdigest()

def verify(label, path, expected):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Missing or symlink {label}: {path}")
    h = digest(path)
    if h != expected:
        raise RuntimeError(f"{label} SHA256 changed (got {h}); stopping before report inspection")
    emit("PASS", f"{label} SHA256", h)

def limited_text(path):
    if not path.is_file() or path.is_symlink():
        return None
    if path.stat().st_size > MAX_REPORT_SIZE:
        return None
    return path.read_text(encoding="utf-8", errors="replace")

def window(lines, index, before=14, after=5):
    lo = max(0, index - before)
    hi = min(len(lines), index + after + 1)
    return [
        {"line": pos+1, "text": lines[pos].rstrip()[:250]}
        for pos in range(lo, hi)
    ]

def inspect_report(path):
    content = limited_text(path)
    if content is None:
        return {"file": str(path), "skipped": "missing/symlink/>8MiB"}
    split = content.splitlines()
    no_path_positions = [i for i, line in enumerate(split) if MARKER.search(line)]
    annot_positions = [i for i, line in enumerate(split) if UNANNOTATED.search(line)]
    warnings = [i for i, line in enumerate(split) if WARNING.search(line)]
    startpoints = STARTPOINT.findall(content)
    endpoints = ENDPOINT.findall(content)
    return {
        "file": str(path),
        "bytes": path.stat().st_size,
        "no_paths_found": len(no_path_positions),
        "no_paths_found_contexts": [window(split, i) for i in no_path_positions[:8]],
        "annotation_markers": len(annot_positions),
        "annotation_examples": [window(split, i, 3, 7) for i in annot_positions[:4]],
        "unconstrained_warning_contexts": [window(split, i, 4, 4) for i in warnings[:8]],
        "startpoints": len(startpoints),
        "endpoints": len(endpoints),
        "startpoint_examples": startpoints[:3],
        "endpoint_examples": endpoints[:3],
    }

def main():
    print("===== ASIC STAGE 2I: UART STA NO-PATHS COVERAGE REVIEW =====", flush=True)
    if getpass.getuser() != "vaish" or os.geteuid() == 0:
        raise RuntimeError("Expected normal non-root Ubuntu user vaish")
    if not TEMP.is_dir():
        raise RuntimeError("G: Temp not mounted; no writes attempted")
    verify("Stage 2F GDS", GDS, EXPECTED_GDS)
    verify("Stage 2C preserved GDS", OLD, EXPECTED_OLD)
    verify("Applied provisional SDC", SDC, EXPECTED_SDC)
    provenance = BASE / "PROVENANCE.txt"
    if not provenance.is_file() or f"Git HEAD: {EXPECTED_REV}" not in provenance.read_text(encoding="utf-8"):
        raise RuntimeError("Stage 2F provenance mismatch")
    emit("PASS", "Stage 2F source", EXPECTED_REV)
    metrics_path = RUN / "final" / "metrics.json"
    if not metrics_path.is_file():
        raise RuntimeError("Expected Stage 2F final metrics.json missing")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if not isinstance(metrics, dict) or len(metrics) != 307:
        raise RuntimeError(f"Unexpected Stage 2F final metrics count {len(metrics) if isinstance(metrics,dict) else 'not mapping'}")
    emit("PASS", "Final metrics", f"{len(metrics)} entries, unannotated raw={metrics.get('timing__unannotated_net__count')}, filtered={metrics.get('timing__unannotated_net_filtered__count')}")
    sta_folders = sorted(
        [p for p in RUN.iterdir() if p.is_dir() and "openroad-stapostpnr" in p.name.lower()]
    )
    if len(sta_folders) != 1:
        raise RuntimeError(f"Expected one OpenROAD STAPostPNR folder, got {len(sta_folders)}")
    sta = sta_folders[0]
    corners = sorted(p for p in sta.iterdir() if p.is_dir())
    if len(corners) != 9:
        emit("REVIEW", "PVT corner folder count", f"Found {len(corners)}; nine expected from Stage 2H")
    details = []
    all_missing_groups = 0
    all_timed_paths = 0
    groups = {}
    for corner in corners:
        reports = sorted(p for p in corner.rglob("*.rpt") if p.is_file() and not p.is_symlink())
        report_data = [inspect_report(p) for p in reports]
        checks = corner / "checks.rpt"
        checks_found = checks.is_file()
        filter_log = corner / "filter_unannotated.log"
        filter_text = limited_text(filter_log)
        marker_count = sum(x.get("no_paths_found", 0) for x in report_data)
        startpoint_count = sum(x.get("startpoints", 0) for x in report_data)
        endpoint_count = sum(x.get("endpoints", 0) for x in report_data)
        all_missing_groups += marker_count
        all_timed_paths += min(startpoint_count, endpoint_count)
        short_groups = []
        for report in report_data:
            if report.get("no_paths_found", 0) > 0:
                base = Path(report["file"]).name
                for frame in report["no_paths_found_contexts"][:2]:
                    matched = [x for x in frame if MARKER.search(x["text"])]
                    snippet = " | ".join(f"L{x['line']}:{x['text']}" for x in frame[-9:])
                    short_groups.append({
                        "report": base,
                        "matched_line": matched[0]["line"] if matched else None,
                        "context": snippet[:500]
                    })
        groups[corner.name] = short_groups
        emit("REPORT", corner.name, f"{len(reports)} *.rpt, {startpoint_count} Startpoint, {endpoint_count} Endpoint mentions; No paths found={marker_count}; checks.rpt={'YES' if checks_found else 'NO'}")
        if short_groups:
            for occurrence in short_groups[:1]:
                emit("NO_PATH", corner.name, f"{occurrence['report']} line {occurrence['matched_line']}; context in JSON")
        if filter_text is not None:
            matches = [x.strip()[:180] for x in filter_text.splitlines()
                       if re.search(r"(?i)(reported nets|filtered nets|unannotated report|net\(|bterm\()", x)]
            if matches:
                emit("INFO", corner.name, f"{len(matches)} filter.log annotation-related line(s); saved in JSON")
        else:
            matches = []
            emit("REVIEW", corner.name, "filter_unannotated.log missing or too large")
        raw_key = "timing__unannotated_net__count__corner:" + corner.name
        filtered_key = "timing__unannotated_net_filtered__count__corner:" + corner.name
        details.append({
            "corner": corner.name,
            "raw_annotation": metrics.get(raw_key),
            "filtered_annotation": metrics.get(filtered_key),
            "checks_rpt_found": checks_found,
            "filter_log_annotation_lines": matches[:120],
            "reports": report_data,
        })
    emit("INFO", "Total report path labels", f"{all_timed_paths} Startpoint/Endpoint pairs (mentions, not verified distinct paths)")
    emit("INFO", "Total No paths found phrases", f"{all_missing_groups} across {len(corners)} corners")
    if all_missing_groups:
        # Show *actual* source context for one example corner on the screen;
        # full 9-corner detail is stored in G: JSON.
        sample = next((x for x in details if groups[x["corner"]]), None)
        if sample:
            corner = sample["corner"]
            report = next(y for y in sample["reports"] if y.get("no_paths_found",0) > 0)
            context = report["no_paths_found_contexts"][0]
            emit("INFO", "Representative No paths found context", f"{corner} / {Path(report['file']).name}")
            for row in context[-9:]:
                emit("CONTEXT", f"L{row['line']}", row["text"][:180])
    if all_missing_groups and all_timed_paths:
        emit("REVIEW", "STA coverage", "Timed path examples exist, but one or more path groups contain 'No paths found'; interpret report context before signoff")
    elif all_missing_groups:
        emit("REVIEW", "STA coverage", "No paths found without evidence of timed paths; further constraint review essential")
    else:
        emit("INFO", "STA coverage", "No 'No paths found' report marker detected")
    emit("INFO", "Timing limitation", "Clock, 0–10 ns IO budgets, load and async RX exception remain provisional")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_out = TEMP / f"ASIC-Stage2I-UART-STA-Contexts-{stamp}.json"
    txt_out = TEMP / f"ASIC-Stage2I-UART-STA-Summary-{stamp}.txt"
    evidence = {
        "scope": "Read-only report-context inspection; not timing/fabrication signoff",
        "run": str(RUN),
        "sha256_gds": EXPECTED_GDS,
        "sha256_sdc": EXPECTED_SDC,
        "source_revision": EXPECTED_REV,
        "metric_unannotated": {
            "raw": metrics.get("timing__unannotated_net__count"),
            "filtered": metrics.get("timing__unannotated_net_filtered__count")
        },
        "reports": details,
        "no_paths_groups_by_corner": groups
    }
    json_out.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    emit("PASS", "Read-only Stage 2I extraction", "No RTL, report, GDS or tool modification")
    emit("INFO", "Evidence JSON", str(json_out))
    emit("INFO", "Compact summary", str(txt_out))
    txt_out.write_text("\n".join(logs) + "\n", encoding="utf-8")
    print("===== END ASIC STAGE 2I =====", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL | Stage 2I | {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
r"""ASIC Stage 2L — READ-ONLY STA path-classification audit.

OpenSTA's report_checks -unconstrained *includes normal constrained paths*.
This script checks whether the reported tx_valid -> _390_ paths actually have
numeric slack, required time, a clock path group and 10ns external input delay.
It separately checks the original check_setup warning on async rx_i.
No STA rerun, Git change, SDC modifications, or layout mutations.
Writes report-only evidence to G:\C-Drive-Backup-PreReset\Temp.
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

TEMP=Path("/mnt/g/C-Drive-Backup-PreReset/Temp")
BASE=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x")
RUN=BASE/"runs/sdc-explore-20261116-074159"
REF=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
NEW=RUN/"final/gds/uart_core.gds"
SDC=BASE/"src/uart_10mhz_provisional.sdc"
PROV=BASE/"PROVENANCE.txt"
METRICS=RUN/"final/metrics.json"
CONFG=RUN/"resolved.json"
REF_HASH="3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
NEW_HASH="d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
SDC_HASH="a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4"
SOURCE="712be2f718757d55f6aa7ab154d05f8d050bacac"
STA_SRC="librelane/scripts/openroad/sta/corner.tcl"
SPECS=((REF,REF_HASH,"Stage 2C GDS"),(NEW,NEW_HASH,"Stage 2F GDS"),(SDC,SDC_HASH,"Stage 2F SDC"))
SLACK=re.compile(r"(?im)^\s*slack\s*(?:\([^)]+\))?\s+([-+]?\d+(?:\.\d*)?)\s*$")
NO_PATHS=re.compile(r"(?i)\bNo paths found\b")
HEADERS={
    "unconstrained":"report_checks -unconstrained",
    "negative":"report_checks --slack_max -0.01",
    "electrical":"report_check_types -max_slew",
    "annotation":"report_parasitic_annotation -report_unannotated",
    "check_setup":"check_setup -verbose",
}
lines=[]

def put(state,label,value):
    entry=f"{state} | {label} | {value}"
    print(entry,flush=True)
    lines.append(entry)

def require(path):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Missing file or symlink: {path}")

def hash_file(path):
    digest=hashlib.sha256()
    with path.open("rb") as f:
        while chunk:=f.read(1048576): digest.update(chunk)
    return digest.hexdigest()

def extract_sections(report):
    require(report)
    if report.stat().st_size>8*1024*1024:
        raise RuntimeError(f"Unexpectedly large STA report: {report}")
    raw=report.read_text(encoding="utf-8",errors="replace").splitlines()
    positions=[]
    for i,line in enumerate(raw):
        for key,label in HEADERS.items():
            if line.strip().startswith(label):
                positions.append((i,key))
                break
    if [name for _,name in positions]!=list(HEADERS):
        raise RuntimeError(f"Unexpected checks.rpt sections: {report}, found {[name for _,name in positions]}")
    return {
        key:{
            "header_line":start+1,
            "body":[{"line":i+1,"text":raw[i].rstrip()[:350]}
                    for i in range(start+1,positions[j+1][0] if j+1<len(positions) else len(raw))],
        }
        for j,(start,key) in enumerate(positions)
    }

def first_line(body,regex):
    pattern=re.compile(regex,re.I)
    for row in body:
        if pattern.search(row["text"]):
            return row["text"].strip()
    return None

def number_from_line(line):
    if line is None: return None
    match=SLACK.search(line)
    return float(match.group(1)) if match else None

def main():
    print("===== ASIC STAGE 2L: UART REAL TIMING PATH COVERAGE AUDIT =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root Ubuntu user vaish")
    if not TEMP.is_dir():
        raise RuntimeError("G: Temp not mounted")
    for path,expected,label in SPECS:
        require(path)
        if hash_file(path)!=expected:
            raise RuntimeError(f"{label} differs from pinned run")
        put("PASS",label,"SHA256 matches preserved baseline")
    for path in (PROV,METRICS,CONFG): require(path)
    if f"Git HEAD: {SOURCE}" not in PROV.read_text(encoding="utf-8"):
        raise RuntimeError("Stage 2F provenance mismatch")
    put("PASS","RTL source provenance",SOURCE)
    metrics=json.loads(METRICS.read_text(encoding="utf-8"))
    resolved=json.loads(CONFG.read_text(encoding="utf-8"))
    if not isinstance(metrics,dict) or len(metrics)!=307 or not isinstance(resolved,dict):
        raise RuntimeError("Unexpected LibreLane metrics or resolved configuration")
    for key in ("PNR_SDC_FILE","SIGNOFF_SDC_FILE"):
        ref=resolved.get(key)
        if not isinstance(ref,str):
            raise RuntimeError(f"{key} unset in resolved config")
        target=Path(ref) if Path(ref).is_absolute() else BASE/Path(ref)
        if target.resolve(strict=True)!=SDC.resolve(strict=True):
            raise RuntimeError(f"{key} not pinned to known SDC")
    put("PASS","Resolved PNR/signoff SDC","Both point to verified Stage 2F SDC")
    sdc=SDC.read_text(encoding="utf-8")
    if "set_false_path -from [get_ports rx_i]" not in sdc or "tx_valid tx_data*" not in sdc:
        raise RuntimeError("Pinned SDC unexpectedly lacks async RX exception or TX input budget")
    sta_steps=[p for p in RUN.iterdir() if p.is_dir() and "openroad-stapostpnr" in p.name.lower()]
    if len(sta_steps)!=1: raise RuntimeError(f"Expected 1 STA step, found {len(sta_steps)}")
    corners=sorted(p for p in sta_steps[0].iterdir() if p.is_dir())
    if len(corners)!=9: raise RuntimeError(f"Expected 9 corners, found {len(corners)}")
    report=[]
    valid_slack=0
    rx_warnings=0
    for corner in corners:
        sections=extract_sections(corner/"checks.rpt")
        u=sections["unconstrained"]["body"]
        n=sections["negative"]["body"]
        check=sections["check_setup"]["body"]
        start=first_line(u,r"Startpoint:\s*tx_valid\b")
        endpoint=first_line(u,r"Endpoint:")
        group=first_line(u,r"Path Group:")
        external=first_line(u,r"input external delay")
        required=first_line(u,r"data required time")
        slack=first_line(u,r"^\s*slack\b")
        numeric_slack=number_from_line(slack)
        has_no_neg=any(NO_PATHS.search(x["text"]) for x in n)
        missing_input=first_line(check,r"missing set_input_delay")
        mentioned_rx=any(re.fullmatch(r"\s*rx_i\s*",r["text"]) for r in check)
        if numeric_slack is not None: valid_slack+=1
        if missing_input and mentioned_rx: rx_warnings+=1
        qualified=(bool(start and endpoint and group and external and required)
                   and numeric_slack is not None and has_no_neg)
        put("REPORT",corner.name,
            f"tx_valid input delay={'YES' if external else 'NO'}; "
            f"required time={'YES' if required else 'NO'}; "
            f"slack={numeric_slack}; "
            f"negative-slack empty={'YES' if has_no_neg else 'NO'}; "
            f"missing input delay port={'rx_i' if mentioned_rx else 'UNRESOLVED'}")
        if not qualified:
            put("REVIEW",corner.name,"Path constraint status cannot be confirmed from all report fields")
        record={
            "corner":corner.name,
            "startpoint":start,"endpoint":endpoint,"path_group":group,
            "input_external_delay_line":external,
            "required_time_line":required,"slack_line":slack,
            "numeric_slack_ns":numeric_slack,
            "negative_slack_query_empty":has_no_neg,
            "check_setup_missing_delay_warning":missing_input,
            "check_setup_rx_i_mentioned":mentioned_rx,
            "qualified_report_path":qualified,
            "original_unconstrained_option_includes_normal_paths":True,
            "all_sections":sections,
            "setup_worst_slack_metric":metrics.get(f"timing__setup__ws__corner:{corner.name}"),
            "hold_worst_slack_metric":metrics.get(f"timing__hold__ws__corner:{corner.name}"),
        }
        report.append(record)
    put("INFO","Actual numeric slack in inclusive -unconstrained report",f"{valid_slack}/9 corners")
    put("INFO","rx_i named in missing-delay warning",f"{rx_warnings}/9 corners")
    if all(item["qualified_report_path"] for item in report):
        put("PASS","tx_valid path classification",
            "Clock-grouped paths have input delay, required time and numeric slack in all 9 saved reports")
    else:
        put("REVIEW","tx_valid path classification",
            "At least one saved report lacks a required timing field; inspect JSON before decisions")
    if rx_warnings==9:
        put("REVIEW","Asynchronous RX warning",
            "check_setup flags rx_i (intentionally false-pathed); do not add synthetic synchronous input delay")
    put("INFO","OpenSTA semantics",
        "report_checks -unconstrained reports unconstrained paths ALSO, not exclusively")
    put("INFO","Signoff boundary",
        "Clock/IO budgets provisional; CDC/MTBF, reset, PDK/IO wrapper and shuttle signoff OPEN")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    evidence=TEMP/f"ASIC-Stage2L-UART-Timing-Classification-{stamp}.json"
    summary=TEMP/f"ASIC-Stage2L-UART-Summary-{stamp}.txt"
    evidence.write_text(json.dumps({
        "scope":"READ ONLY; report-only path classification, NOT timing signoff",
        "source_opensta_docs":"https://opensta.readthedocs.io/en/latest/Commands/",
        "source_librelane_sta_script":STA_SRC,
        "source_commit":SOURCE,
        "gds_sha256":NEW_HASH,
        "sdc_sha256":SDC_HASH,
        "corners":report,
    },indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    put("PASS","Stage 2L report extraction","9 PVT corner reports reviewed, no source or layout changed")
    put("INFO","Detailed G: evidence",str(evidence))
    put("INFO","Compact G: summary",str(summary))
    summary.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 2L =====",flush=True)

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"FAIL | Stage 2L audit | {type(e).__name__}: {e}",file=sys.stderr)
        sys.exit(1)

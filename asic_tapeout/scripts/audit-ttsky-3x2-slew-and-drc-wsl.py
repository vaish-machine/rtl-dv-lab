#!/usr/bin/env python3
r"""ASIC Stage 3G: READ-ONLY TT SKY130 3x2 slew and missing DRC audit.

Inspect only the completed, preserved Stage 3E local physical run:
* confirm final GDSII SHA256 and original Stage2C/2F GDS/SDC SHA256,
* read LibreLane final metrics and identify exact slow-corner max-slew counts,
* determine whether KLayout DRC was disabled in the official template config,
* locate and excerpt any saved slew / STA report diagnostics,
* distinguish total physical instance area from actual functional placement use.

No EDA run, no GDS changes, no PDK modifications, no provider CI/precheck,
no real shuttle signoff. Save evidence only to G:\C-Drive-Backup-PreReset\Temp.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys

TEMP=Path("/mnt/g/C-Drive-Backup-PreReset/Temp")
ROOT=Path("/home/vaish/DevTools/LibreLane/ttsky_sky130_3x2_trial/run-46NnPce8")
TEMPLATE=ROOT/"template"
RUN=TEMPLATE/"src/runs/tt-3x2-20261116-123932"
GDS=RUN/"final/gds/tt_um_vaish_uart.gds"
METRICS=RUN/"final/metrics.json"
FLOW_LOG=ROOT/"physical-flow.log"
CONFIG=TEMPLATE/"src/config.json"
MERGED=TEMPLATE/"src/config_merged.json"
OLD2C=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
OLD2F=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds")
SDC=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc")
PINNED={
    GDS:"4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599",
    OLD2C:"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3",
    OLD2F:"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af",
    SDC:"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4",
}
LOG=[]
DETAILS={
    "scope":"READ-ONLY existing local TT 3x2 metrics, slew and DRC; NOT actual provider precheck",
    "run_dir":str(RUN),
}
SLEW_RE=re.compile(r"(?i)(max.?slew|slew.?violat|slew.?limit|report_check_types.+slew)")
SECTIONS_RE=re.compile(r"(?i)(report_check_types|max.slew|slew|check_setup)")
MAX_REPORTS=650

def emit(status,name,value):
    line=f"{status} | {name} | {value}"
    print(line,flush=True)
    LOG.append(line)

def file(path,label):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label}: missing file or symlink: {path}")
    return path

def hash_data(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def get_json(path,label):
    file(path,label)
    if path.stat().st_size>20*1024*1024:
        raise RuntimeError(f"Unexpected oversized JSON: {label}")
    val=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(val,dict):
        raise RuntimeError(f"{label} must be JSON object")
    return val

def enforce_old_inputs():
    for loc,wanted in PINNED.items():
        file(loc,loc.name)
        actual=hash_data(loc)
        if actual!=wanted:
            raise RuntimeError(f"{loc}: expected SHA256 {wanted}, observed {actual}")
        name="Stage 3E final 3x2 GDS" if loc==GDS else ("Original Stage 2C GDS" if loc==OLD2C else ("Original Stage 2F GDS" if loc==OLD2F else "Original Stage 2F SDC"))
        emit("PASS",name,f"SHA256 unchanged ({wanted[:16]}...)")
    emit("INFO","Final TT trial GDS",f"{GDS.stat().st_size} bytes; no GDS edits")
    DETAILS["final_gds"]={"path":str(GDS),"sha256":PINNED[GDS],"bytes":GDS.stat().st_size}

def summarize_config():
    official=get_json(CONFIG,"Stage 3E copied official template config")
    active=get_json(MERGED,"Stage 3E merged config")
    if active.get("DESIGN_NAME")!="tt_um_vaish_uart":
        raise RuntimeError("Stage 3E merged top unexpectedly differs")
    if active.get("FP_DEF_TEMPLATE")!="dir::../tt/tech/sky130A/def/tt_block_3x2_pg.def":
        raise RuntimeError("Stage 3E merged DEF path unexpected")
    if Decimal(str(active.get("CLOCK_PERIOD")))!=Decimal(100):
        raise RuntimeError("Stage 3E experimental 100 ns clock unexpectedly changed")
    if Decimal(str(active.get("DIE_AREA").split()[2]))!=Decimal("508.76"):
        raise RuntimeError("Stage 3E 3x2 die rectangle unexpectedly changed")
    for key in ("RUN_KLAYOUT_DRC","RUN_KLAYOUT_XOR","PL_TARGET_DENSITY_PCT",
                "CLOCK_PERIOD","RUN_CTS","RUN_LINTER"):
        emit("CONFIG",key,f"template={official.get(key, 'NOT SET')}; active={active.get(key, 'NOT SET')}")
    klayout=active.get("RUN_KLAYOUT_DRC")
    if klayout in (0,False):
        emit("REVIEW","KLayout DRC","Explicitly disabled by trial/template config; missing metric is NOT a clean DRC result")
    elif klayout is None:
        emit("REVIEW","KLayout DRC","No explicit setting located; check actual final flow step presence")
    else:
        emit("REVIEW","KLayout DRC","Enabled in config but final metric absent; determine whether step completed")
    emit("PASS","TT 3x2 floorplan input","508.76 x 225.76 um, explicit 100 ns exploratory clock; not real shuttle IO signoff")
    DETAILS["config"]={"official":{k:official.get(k) for k in ("RUN_KLAYOUT_DRC","RUN_KLAYOUT_XOR","PL_TARGET_DENSITY_PCT","CLOCK_PERIOD")},
                       "active":{k:active.get(k) for k in ("RUN_KLAYOUT_DRC","RUN_KLAYOUT_XOR","PL_TARGET_DENSITY_PCT","CLOCK_PERIOD","DIE_AREA","FP_DEF_TEMPLATE","RUN_CTS","RUN_LINTER")}}

def summarize_metrics():
    d=get_json(METRICS,"Stage 3E final metrics")
    if len(d)<200:
        raise RuntimeError(f"Stage 3E final metrics incomplete ({len(d)})")
    emit("PASS","Stage 3E final metrics",f"{len(d)} keys from exact final physical run")
    DETAILS["metrics_path"]=str(METRICS)
    selected=[
        "design__instance__area","design__instance__count","design__core__area",
        "route__drc_errors","magic__drc_error__count","klayout__drc_error__count",
        "design__lvs_error__count","timing__setup_vio__count","timing__hold_vio__count",
        "timing__setup__wns","timing__hold__wns",
        "design__max_slew_violation__count",
    ]
    DETAILS["selected_metrics"]={k:d.get(k) for k in selected}
    for key in selected:
        val=d.get(key,"UNAVAILABLE")
        if key=="klayout__drc_error__count":
            emit("REVIEW",key,"Not reported (not equivalent to DRC=0)" if val=="UNAVAILABLE" else val)
        elif key=="design__max_slew_violation__count":
            emit("REVIEW",key,val)
        elif val=="UNAVAILABLE":
            emit("REVIEW",key,"Not reported")
        elif isinstance(val,(int,float)) and val!=0 and any(x in key for x in ("drc","lvs_error","vio__count")):
            emit("REVIEW",key,val)
        else:
            emit("METRIC",key,val)
    corners=[]
    for key,val in d.items():
        if "max_slew_violation__count__corner:" in key:
            corners.append((key.split("corner:",1)[1],val))
    for corner,val in sorted(corners):
        emit("REVIEW" if val else "METRIC","Max-slew "+corner,f"{val} violation(s)")
    DETAILS["max_slew_by_corner"]=dict(corners)
    positive={k:v for k,v in corners if isinstance(v,(int,float)) and v>0}
    if positive:
        emit("REVIEW","Max-slew readiness",
             "Nonzero violations at "+", ".join(sorted(positive))+"; detailed endpoints and timing repair needed")
    if "design__max_slew_violation__count" in d:
        emit("INFO","Slew counting caveat","Aggregate count is not the sum of per-corner violations; avoid double counting")
    area=d.get("design__instance__area")
    if isinstance(area,(int,float)):
        pct=Decimal(str(area))/Decimal("114857.6576")*Decimal(100)
        emit("INFO","Reported instance area vs 3x2 die",f"{pct:.2f}% (includes potentially filler/physical-only; NOT proof of functional-cell utilization)")
    possibly_physical=[
        (k,v) for k,v in d.items()
        if re.search(r"(?i)(filler|physical.?only|decap|tapcell|stdcell|utilization|density)",k)
    ]
    DETAILS["possible_utilization_breakdown"]={k:v for k,v in possibly_physical[:100]}
    for key,val in possibly_physical[:22]:
        emit("EVIDENCE","Physical-cell/utilization metric",f"{key}={val}")
    if not possibly_physical:
        emit("REVIEW","Functional-cell utilization","No filler-stripped usable area metric; do not infer from instance area")
    return d

def scan_sta_report_clues():
    """Target saved report files, not PDK or source clones; never rerun STA."""
    scanned=0
    matched=[]
    paths=[]
    for path in RUN.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in {".rpt",".log",".txt"}:
            continue
        paths.append(path)
        if len(paths)>=MAX_REPORTS:
            break
    for p in sorted(paths):
        if p.stat().st_size>6*1024*1024:
            continue
        scanned+=1
        try:
            with p.open(encoding="utf-8",errors="replace") as f:
                lines=f.readlines()
        except OSError:
            continue
        hit_indices=[i for i,line in enumerate(lines) if SLEW_RE.search(line)]
        if not hit_indices:
            continue
        excerpts=[]
        for i in hit_indices[:5]:
            excerpts.append({
                "line":i+1,
                "context":[line.rstrip()[:240] for line in lines[max(i-2,0):min(i+3,len(lines))]],
            })
        matched.append({"path":str(p),"match_count":len(hit_indices),"excerpts":excerpts})
    put_n=len(matched)
    emit("INFO","STA/report text files inspected",scanned)
    emit("INFO","Reports mentioning slew",put_n)
    for record in matched[:9]:
        emit("REPORT","Slew evidence",f"{record['path']} ({record['match_count']} matching lines)")
        for excerpt in record["excerpts"][:2]:
            line=" | ".join(x.strip() for x in excerpt["context"] if x.strip())
            emit("CONTEXT",f"line {excerpt['line']}",line[:300])
    DETAILS["slew_report_candidates"]=matched
    if not matched:
        emit("REVIEW","Exact failing endpoints",
             "No slew-specific text in preserved reports. Do not invent net/pin names; detailed STA follow-up required")
    elif len(matched)>9:
        emit("INFO","Further slew reports",f"{len(matched)-9} locations recorded in detailed JSON")
    return matched

def log_warning_context():
    file(FLOW_LOG,"Stage 3E physical flow log")
    warnings=[]
    with FLOW_LOG.open(encoding="utf-8",errors="replace") as stream:
        for n,line in enumerate(stream,1):
            if re.search(r"(?i)(MaxSlewViolations|klayout__drc_error__count not reported|IRDropReport|Check for LVS errors clear|Setup Timing Violations Checker)",line):
                warnings.append({"line":n,"text":line.strip()[:420]})
                if len(warnings)>50:
                    break
    DETAILS["physical_flow_warnings"]=warnings
    for item in warnings[:12]:
        emit("LOG",f"line {item['line']}",item["text"][:300])

def main():
    print("===== ASIC STAGE 3G: TT 3X2 MAX SLEW AND KLAYOUT DRC AUDIT =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root WSL Ubuntu user vaish")
    if not TEMP.is_dir() or not RUN.is_dir():
        raise RuntimeError("Missing G: Temp mount or exact preserved Stage3E run")
    enforce_old_inputs()
    summarize_config()
    summarize_metrics()
    scan_sta_report_clues()
    log_warning_context()
    emit("REVIEW","Physical signoff",
         "Route/Magic DRC/LVS 0 is useful local evidence; max slew and KLayout DRC/actual TT precheck remain OPEN")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    detailed=TEMP/f"ASIC-Stage3G-TTSKY-3x2-Slew-DRC-{stamp}.json"
    compact=TEMP/f"ASIC-Stage3G-TTSKY-3x2-Summary-{stamp}.txt"
    detailed.write_text(json.dumps(DETAILS,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    emit("PASS","Read-only Stage 3G","Original TT GDS, RTL, PDK, SDC and prior logs unchanged")
    emit("INFO","Detailed G: evidence",str(detailed))
    emit("INFO","Compact G: summary",str(compact))
    compact.write_text("\n".join(LOG)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3G =====",flush=True)

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL | Stage 3G | {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)

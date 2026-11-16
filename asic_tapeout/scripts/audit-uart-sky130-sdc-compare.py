#!/usr/bin/env python3
r"""Stage 2G: independent read-only comparison of the two G:-backed UART GDS runs.

Verifies both exact SHA256 GDS files, the constrained run's resolved timing
config and SDC file, and compares final selected metrics (not metric ranges).
Writes only audit JSON + compact text to G:\C-Drive-Backup-PreReset\Temp.
No Git operations, PDK changes, EDA rerun, or alteration of original artifacts.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from datetime import datetime

ROOT=Path("/mnt/g/C-Drive-Backup-PreReset")
TEMP=ROOT/"Temp"
REF_WORK=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du")
REF_RUN=REF_WORK/"runs/explore-20261116-061728"
NEW_WORK=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x")
NEW_RUN=NEW_WORK/"runs/sdc-explore-20261116-074159"
REF_GDS=REF_RUN/"final/gds/uart_core.gds"
NEW_GDS=NEW_RUN/"final/gds/uart_core.gds"
REF_SHA="3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
NEW_SHA="d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
REF_SIZE=2053232
NEW_SIZE=2065964
REF_REV="2ed57ff4cff277242cbcc397de0c2ee009c7eb1b"
NEW_REV="712be2f718757d55f6aa7ab154d05f8d050bacac"
EXPECTED_SDC=NEW_WORK/"src/uart_10mhz_provisional.sdc"
REF_LOG=REF_WORK/"librelane-explore-20261116-061728.log"
NEW_LOG=NEW_WORK/"librelane-sdc-explore-20261116-074159.log"
METRICS=[
    ("Routing DRC", "route__drc_errors"),
    ("Magic DRC", "magic__drc_error__count"),
    ("KLayout DRC", "klayout__drc_error__count"),
    ("LVS errors", "design__lvs_error__count"),
    ("LVS unmatched devices", "design__lvs_unmatched_device__count"),
    ("Setup violations", "timing__setup_vio__count"),
    ("Hold violations", "timing__hold_vio__count"),
    ("Setup WNS", "timing__setup__wns"),
    ("Hold WNS", "timing__hold__wns"),
    ("Setup TNS", "timing__setup__tns"),
    ("Hold TNS", "timing__hold__tns"),
    ("Unannotated nets", "timing__unannotated_net__count"),
    ("Instance count", "design__instance__count"),
    ("Instance area", "design__instance__area"),
    ("Core area", "design__core__area"),
    ("Utilization", "design__instance__utilization"),
    ("Total power", "power__total"),
]
def out(level, heading, msg, lines):
    s=f"{level} | {heading} | {msg}"
    print(s, flush=True)
    lines.append(s)

def fail(message, lines):
    out("FAIL","Stage 2G audit",message,lines)
    raise RuntimeError(message)

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while block:=f.read(1024*1024): h.update(block)
    return h.hexdigest()

def expect_gds(label,path,expected_size,expected_sha,lines):
    if not path.is_file() or path.is_symlink():
        fail(f"Missing or symlink {label} GDSII: {path}",lines)
    size=path.stat().st_size
    if size!=expected_size: fail(f"{label} GDS size mismatch {size}",lines)
    actual=sha256(path)
    if actual!=expected_sha: fail(f"{label} GDS SHA256 mismatch {actual}",lines)
    out("PASS",f"{label} GDS integrity",f"{size} bytes, {actual}",lines)

def read_json(path):
    if not path.is_file(): raise RuntimeError(f"Missing JSON: {path}")
    with path.open(encoding="utf-8") as f: return json.load(f)

def number(x):
    if isinstance(x,bool): return None
    if isinstance(x,(float,int,str)):
        try:
            y=float(x)
            if math.isfinite(y): return y
        except ValueError: pass
    return None

def sdc_reference(config,key):
    ref=config.get(key)
    if ref is None: return (False,"missing")
    if not isinstance(ref,str): return (False,f"not a path string: {type(ref).__name__}")
    if ref.startswith("dir::"): return (False,f"unresolved dir:: URI: {ref}")
    normalized=Path(ref)
    if not normalized.is_absolute(): normalized=NEW_WORK/normalized
    try:
        actual=normalized.resolve(strict=True)
        expected=EXPECTED_SDC.resolve(strict=True)
    except OSError as e: return (False,f"cannot resolve referenced SDC path {ref}: {e}")
    return (actual==expected,f"{ref} -> {actual}")

def main():
    lines=[]
    print("===== ASIC STAGE 2G: UART CONSTRAINED VS REFERENCE AUDIT =====",flush=True)
    if os.geteuid()==0 or os.getenv("USER")!="vaish":
        print("FAIL | Expected normal Ubuntu user vaish",flush=True)
        return 1
    if not TEMP.is_dir():
        print("FAIL | G: Temp directory unavailable",flush=True)
        return 1
    try:
        expect_gds("Stage 2C reference",REF_GDS,REF_SIZE,REF_SHA,lines)
        expect_gds("Stage 2F constrained",NEW_GDS,NEW_SIZE,NEW_SHA,lines)
        for label,work,revision in [
            ("Stage 2C",REF_WORK,REF_REV),("Stage 2F",NEW_WORK,NEW_REV)]:
            provenance=work/"PROVENANCE.txt"
            if not provenance.is_file() or f"Git HEAD: {revision}" not in provenance.read_text(encoding="utf-8"):
                fail(f"{label} provenance source commit mismatch",lines)
            out("PASS",f"{label} provenance",revision,lines)
        ref_metrics=read_json(REF_RUN/"final/metrics.json")
        new_metrics=read_json(NEW_RUN/"final/metrics.json")
        if not isinstance(ref_metrics,dict) or not isinstance(new_metrics,dict):
            fail("Invalid metrics JSON type",lines)
        out("PASS","Metrics sources",f"{len(ref_metrics)} reference keys, {len(new_metrics)} constrained keys",lines)
        if not REF_LOG.is_file() or not NEW_LOG.is_file():
            fail("Original LibreLane logs absent",lines)
        log0=REF_LOG.read_text(encoding="utf-8",errors="replace")
        log1=NEW_LOG.read_text(encoding="utf-8",errors="replace")
        fallback_warnings=[
            "'PNR_SDC_FILE' is not defined",
            "'SIGNOFF_SDC_FILE' is not defined",
        ]
        ref_fallback=any(s in log0 for s in fallback_warnings)
        new_fallback=any(s in log1 for s in fallback_warnings)
        out("INFO","Reference SDC",f"Generic fallback warning present: {ref_fallback}",lines)
        if new_fallback:
            out("REVIEW","New SDC","Fallback warning present in constrained run; inspect log",lines)
        else:
            out("PASS","New SDC warning scan","No generic fallback warning found",lines)

        resolved_path=NEW_RUN/"resolved.json"
        cfg=read_json(resolved_path)
        if not isinstance(cfg,dict):
            fail("Resolved configuration not JSON object",lines)
        sdc_checks={}
        for key in ("PNR_SDC_FILE","SIGNOFF_SDC_FILE"):
            ok,detail=sdc_reference(cfg,key)
            sdc_checks[key]={"matches_expected":ok,"detail":detail}
            out("PASS" if ok else "REVIEW",key,detail,lines)
        checks={
            "CLOCK_PORT":cfg.get("CLOCK_PORT"),
            "CLOCK_PERIOD":cfg.get("CLOCK_PERIOD"),
            "DESIGN_NAME":cfg.get("DESIGN_NAME"),
            "FP_SIZING":cfg.get("FP_SIZING"),
            "DIE_AREA":cfg.get("DIE_AREA"),
        }
        out("INFO","Resolved physical config",json.dumps(checks,sort_keys=True),lines)
        if not EXPECTED_SDC.is_file():
            fail(f"Actual constrained SDC missing: {EXPECTED_SDC}",lines)
        sdc_content=EXPECTED_SDC.read_text(encoding="utf-8")
        sdc_sha=sha256(EXPECTED_SDC)
        expected_fragments=[
            "create_clock -name uart_clk -period 100.0 [get_ports clk]",
            "set_input_delay -max 10.0",
            "set_input_delay -min 0.0",
            "set_output_delay -max 10.0",
            "set_output_delay -min 0.0",
            "set_false_path -from [get_ports rx_i]",
        ]
        absent=[f for f in expected_fragments if f not in sdc_content]
        if absent:
            out("REVIEW","SDC contents",f"Missing expected statements: {absent}",lines)
        else:
            out("PASS","Staged SDC contents","Clock, IO delays and rx_i exception markers found",lines)
        out("INFO","Applied SDC SHA256",sdc_sha,lines)
        # Compare EXACT unqualified metrics. Never turn counts into ranges,
        # never label positive cell count an error. Raw evidence retained.
        metric_diff={}
        for label,key in METRICS:
            old=ref_metrics.get(key)
            new=new_metrics.get(key)
            metric_diff[key]={"reference":old,"constrained":new}
            old_s="MISSING" if old is None else str(old)
            new_s="MISSING" if new is None else str(new)
            out("METRIC",label,f"Stage2C={old_s}; Stage2F={new_s}",lines)
            if key in {
                "route__drc_errors","magic__drc_error__count",
                "klayout__drc_error__count","design__lvs_error__count",
                "timing__setup_vio__count","timing__hold_vio__count"
            }:
                nn=number(new)
                if nn is None:
                    out("REVIEW",label,"No numeric final value; cannot claim clean",lines)
                elif nn>0:
                    out("REVIEW",label,f"Nonzero final constrained metric {nn}",lines)
        # Keep timing corner-specific raw keys for both variants.
        prefixes=("timing__setup__wns","timing__hold__wns",
                  "timing__setup_vio__count","timing__hold_vio__count",
                  "route__drc_errors")
        corners={
            label:{
                k:v for k,v in sorted(data.items())
                if any(k.startswith(p+"__") for p in prefixes)
            }
            for label,data in [("reference",ref_metrics),("constrained",new_metrics)]
        }
        for label, d in corners.items():
            out("INFO",label+" corner/iteration metrics",f"{len(d)} raw entries saved in audit JSON",lines)
        out("INFO","Timing signoff","OPEN: provisional clock/IO budgets; no real wrapper or CDC/MTBF signoff",lines)
        stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
        evidence=TEMP/f"ASIC-Stage2G-UART-Comparison-{stamp}.json"
        summary=TEMP/f"ASIC-Stage2G-UART-Summary-{stamp}.txt"
        record={
            "scope":"READ-ONLY, provisional SDC consistency and metrics comparison; not tapeout signoff",
            "reference_run":str(REF_RUN),"constrained_run":str(NEW_RUN),
            "reference_gds_sha256":REF_SHA,"constrained_gds_sha256":NEW_SHA,
            "resolved_sdc_checks":sdc_checks,"resolved_config_subset":checks,
            "staged_sdc_sha256":sdc_sha,"staged_sdc_missing_markers":absent,
            "reference_generic_sdc_warning":ref_fallback,
            "constrained_generic_sdc_warning":new_fallback,
            "exact_final_metrics":metric_diff,
            "per_corner_and_iter_metrics":corners,
            "all_reference_metrics":ref_metrics,
            "all_constrained_metrics":new_metrics,
        }
        evidence.write_text(json.dumps(record,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
        out("PASS","Stage 2G read-only extraction","Both GDSII and metric sets compared",lines)
        out("INFO","Full comparison JSON",str(evidence),lines)
        out("INFO","Compact audit text",str(summary),lines)
        summary.write_text("\n".join(lines)+"\n",encoding="utf-8")
        print("===== END ASIC STAGE 2G =====",flush=True)
        return 0
    except Exception as e:
        out("FAIL","Stage 2G",f"{type(e).__name__}: {e}",lines)
        return 1

if __name__=="__main__":
    sys.exit(main())

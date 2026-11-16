#!/usr/bin/env python3
"""ASIC Stage 3F: READ-ONLY locate outputs from the completed Stage 3E TT 3x2 run.

Scans only the exact Stage 3E preserved workspace. Verifies the immutable
Stage 2C/2F GDSII files and SDC; finds any alternate LibreLane run directory;
prints conservative metrics and known physical-rule warnings. No new EDA run,
no source/PDK/GDS edits, no provider CI, no signoff or shuttle submission.
Saves evidence exclusively under G:\C-Drive-Backup-PreReset\Temp.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path("/mnt/g/C-Drive-Backup-PreReset")
TEMP=ROOT/"Temp"
WORK=Path("/home/vaish/DevTools/LibreLane/ttsky_sky130_3x2_trial/run-46NnPce8")
FLOW_LOG=WORK/"physical-flow.log"
TEMPLATE=WORK/"template"
PROV=TEMPLATE/"LOCAL_TRIAL_PROVENANCE.json"
CONFIG=TEMPLATE/"src/config_merged.json"
GDS_2C=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
GDS_2F=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds")
SDC=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc")
EXPECTED=[
    (GDS_2C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Original Stage 2C GDS"),
    (GDS_2F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Original Stage 2F GDS"),
    (SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Provisional Stage 2F SDC"),
]
NOTES=[]
METRIC_KEYS=(
    "design__instance__area","design__instance__count","design__core__area",
    "route__drc_errors","magic__drc_error__count","klayout__drc_error__count",
    "design__lvs_error__count","timing__setup_vio__count",
    "timing__hold_vio__count","timing__setup__wns",
    "timing__hold__wns","power__total"
)

def put(status,label,value):
    line=f"{status} | {label} | {value}"
    NOTES.append(line)
    print(line,flush=True)

def assert_file(path,label):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label}: missing file or symbolic link: {path}")
    return path

def sha(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for buf in iter(lambda:stream.read(1024*1024),b""):
            digest.update(buf)
    return digest.hexdigest()

def under(path,base):
    return path.resolve(strict=True).is_relative_to(base.resolve(strict=True))

def read_json(path,label,max_bytes=16*1024*1024):
    assert_file(path,label)
    if path.stat().st_size>max_bytes:
        raise RuntimeError(f"{label} unexpectedly large")
    return json.loads(path.read_text(encoding="utf-8"))

def scan_paths():
    """Bounded walk, no symlinks, and skip cloned support-tools .git."""
    candidates=[]
    metric_files=[]
    unexpected=[]
    inspected=0
    for dirpath,dirs,files in os.walk(WORK,followlinks=False):
        d=Path(dirpath)
        dirs[:]=sorted(x for x in dirs if x not in {".git","tt","venv","__pycache__"} and not (d/x).is_symlink())
        inspected+=1
        if inspected>12000:
            raise RuntimeError("Scan exceeded 12,000 directory limit; no files changed")
        for name in files:
            if name in {"tt_um_vaish_uart.gds","metrics.json","resolved.json"}:
                item=d/name
                if item.is_symlink() or not under(item,WORK):
                    unexpected.append(str(item))
                    continue
                if name=="tt_um_vaish_uart.gds":
                    candidates.append(item)
                elif name=="metrics.json":
                    metric_files.append(item)
    return sorted(candidates),sorted(metric_files),unexpected,inspected

def report_log():
    assert_file(FLOW_LOG,"Existing Stage 3E physical log")
    recent=deque(maxlen=18)
    counters={"max_slew":0,"klayout_missing":0,"lvs_clear":0,"process_end":0}
    clues=[]
    with FLOW_LOG.open(encoding="utf-8",errors="replace") as stream:
        for n,line in enumerate(stream,1):
            if len(line)>24000:
                continue
            text=line.strip()
            if "MaxSlewViolations" in text:
                counters["max_slew"]+=1
            if "klayout__drc_error__count not reported" in text:
                counters["klayout_missing"]+=1
            if "Check for LVS errors clear" in text:
                counters["lvs_clear"]+=1
            if re.search(r"(?i)(flow complete|flow finished|run complete|flow successful)",text):
                counters["process_end"]+=1
            if ("runs/" in text or "tt_um_vaish_uart.gds" in text) and len(clues)<14:
                clues.append({"line":n,"text":text[:300]})
            recent.append(text[:300])
    put("REPORT","Flow final checker summary",
        f"LVS-clear lines={counters['lvs_clear']}; MaxSlew warning mentions={counters['max_slew']}; unreported KLayout DRC mentions={counters['klayout_missing']}")
    if counters["max_slew"]:
        put("REVIEW","Max-slew violations",
            "Warnings in slow corners; no physical or timing signoff until root-caused")
    if counters["klayout_missing"]:
        put("REVIEW","KLayout DRC",
            "Metrics not reported/skipped; do not claim KLayout DRC clean")
    return {"counters":counters,"path_clues":clues,"tail":list(recent)}

def main():
    print("===== ASIC STAGE 3F: TT 3X2 SAVED OUTPUT LOCATION AND PHYSICAL METRICS =====",flush=True)
    if os.geteuid()==0 or os.getlogin()=="root":
        raise RuntimeError("Run under Ubuntu vaish, not root")
    if not TEMP.is_dir() or not TEMPLATE.is_dir():
        raise RuntimeError("Expected G: Temp or exact Stage 3E workspace missing")
    if os.path.islink(WORK):
        raise RuntimeError("Unexpected symbolic-link workspace")
    for path,wanted,label in EXPECTED:
        assert_file(path,label)
        if sha(path)!=wanted:
            raise RuntimeError(f"{label}: unexpected changed hash")
        put("PASS",label,"Pinned SHA256 unchanged")
    prov=read_json(PROV,"Stage 3E trial provenance")
    config=read_json(CONFIG,"Stage 3E merged config")
    if (prov.get("tile")!="3x2" or prov.get("provider_gds_precheck") is not False or
        config.get("DESIGN_NAME")!="tt_um_vaish_uart" or
        config.get("FP_DEF_TEMPLATE")!="dir::../tt/tech/sky130A/def/tt_block_3x2_pg.def" or
        str(config.get("CLOCK_PERIOD")) not in {"100","100.0"}):
        raise RuntimeError("Existing Stage 3E pinned trial manifest/config do not match")
    put("PASS","Saved Stage 3E inputs","3x2 TT DEF and 100ns experimental clock confirmed")
    evidence_log=report_log()
    candidates,metrics,unexpected,scanned=scan_paths()
    put("INFO","Directories inspected",scanned)
    put("INFO","GDS candidates found",len(candidates))
    put("INFO","metrics.json files found",len(metrics))
    if unexpected:
        put("REVIEW","Unexpected artifact symlinks",f"{len(unexpected)} ignored")
    findings=[]
    chosen=0
    for gds in candidates:
        run=gds.parent.parent.parent
        if gds.parent.name!="gds" or gds.parent.parent.name!="final" or "runs" not in run.parts:
            put("REVIEW","Unrecognized GDS path",str(gds))
            continue
        runmeta=run/"final/metrics.json"
        alternate=run/"metrics.json"
        match=runmeta if runmeta.is_file() else (alternate if alternate.is_file() else None)
        if not match:
            put("REVIEW","GDS metrics missing",str(gds))
            findings.append({"gds":str(gds),"metrics":None})
            continue
        if gds.stat().st_size < 5000:
            put("REVIEW","GDS size unusually small",f"{gds} {gds.stat().st_size} bytes")
            continue
        m=read_json(match,"Stage 3E final metrics")
        if not isinstance(m,dict) or len(m)<50:
            put("REVIEW","Final metrics incomplete",f"{match}: {len(m) if isinstance(m,dict) else 'not dict'} keys")
            continue
        resolved=run/"resolved.json"
        info=None
        if resolved.is_file():
            info=read_json(resolved,"Stage 3E resolved config")
            if info.get("DESIGN_NAME") not in ("tt_um_vaish_uart",None):
                put("REVIEW","Unexpected resolved design",str(info.get("DESIGN_NAME")))
                continue
        chosen+=1
        put("PASS","Local TT trial GDS located",str(gds))
        put("METRIC","GDS size and SHA256",f"{gds.stat().st_size} bytes; {sha(gds)}")
        put("PASS","Final metrics located",f"{len(m)} keys at {match}")
        put("INFO","Run directory",str(run))
        for key in METRIC_KEYS:
            v=m.get(key)
            if v is None:
                put("REVIEW",key,"Not reported in final metrics")
            elif any(part in key for part in ("drc","lvs_error","vio__count")) and isinstance(v,(int,float)) and v>0:
                put("REVIEW",key,v)
            else:
                put("METRIC",key,v)
        slews=[(key,value) for key,value in m.items() if "slew" in key.lower()]
        bad=[(key,value) for key,value in slews if "vio" in key.lower() or "violat" in key.lower()]
        for key,value in bad[:12]:
            put("REVIEW" if isinstance(value,(int,float)) and value>0 else "METRIC",
                key,value)
        findings.append({
            "gds":str(gds),"gds_size_bytes":gds.stat().st_size,
            "gds_sha256":sha(gds),"run_directory":str(run),"metrics":str(match),
            "metrics_count":len(m),"selected_metrics":{k:m.get(k) for k in METRIC_KEYS},
            "slew_metrics":dict(slews),"resolved_config":str(resolved) if resolved.is_file() else None,
        })
    if chosen:
        put("PASS","Stage 3E artifact location",
            f"{chosen} GDS + metrics pair(s) located without rerunning LibreLane")
        put("REVIEW","Readiness","Trial physical artifacts found, but max slew and KLayout DRC reporting require review")
    else:
        put("REVIEW","Stage 3E artifact location",
            "No matching final GDS and metrics pair; use recorded path inventory before any rerun")
        for item in metrics[:12]:
            put("INFO","Saved metrics candidate",str(item))
    for label in ("Stage 2C GDS","Stage 2F GDS","Provisional SDC"):
        pass
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    details=TEMP/f"ASIC-Stage3F-TTSKY-3x2-Artifact-Discovery-{stamp}.json"
    compact=TEMP/f"ASIC-Stage3F-TTSKY-3x2-Summary-{stamp}.txt"
    details.write_text(json.dumps({
        "scope":"Read-only saved Stage3E GDS discovery; NOT provider GDS Action, DRC or signoff",
        "workspace":str(WORK),"template":str(TEMPLATE),
        "provenance":prov,"config":config,
        "log":evidence_log,"all_candidates":[str(x) for x in candidates],
        "all_metrics":[str(x) for x in metrics],
        "unexpected_artifacts":unexpected,"paired_artifacts":findings,
        "directory_scan_count":scanned,
    },indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    put("PASS","Read-only artifact audit","No original design, GDS, SDC or PDK modified")
    put("INFO","Detailed G: evidence",str(details))
    put("INFO","Compact G: summary",str(compact))
    compact.write_text("\n".join(NOTES)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3F =====",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as ex:
        print(f"FAIL | Stage 3F | {type(ex).__name__}: {ex}",file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
r"""ASIC Stage 2J: precise READ-ONLY inspection of OpenSTA checks.rpt sections.

Pin the previously verified Stage 2C/2F GDSII, Stage 2F SDC and source
revision. Inspect *unconstrained* path section separately from the
*-slack_max -0.01* violator section in all nine post-route PVT corners.
Also examine check_setup, clock propagation and actual worst slack.
Only writes output JSON + compact summary to G:\C-Drive-Backup-PreReset\Temp.
Never invokes EDA, Git, or modifies source, old layout, reports or PDK.
"""
from __future__ import annotations

from datetime import datetime
import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT=Path("/mnt/g/C-Drive-Backup-PreReset")
TEMP=ROOT/"Temp"
BASE=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x")
RUN=BASE/"runs/sdc-explore-20261116-074159"
OLD=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
GDS=RUN/"final/gds/uart_core.gds"
SDC=BASE/"src/uart_10mhz_provisional.sdc"
CFG=RUN/"resolved.json"
METRICS=RUN/"final/metrics.json"
PROV=BASE/"PROVENANCE.txt"
HEAD="712be2f718757d55f6aa7ab154d05f8d050bacac"
DIGESTS=[
    ("Constrained Stage 2F GDS",GDS,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"),
    ("Original Stage 2C GDS",OLD,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"),
    ("Provisional Stage 2F SDC",SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4"),
]
HEADERS=[
    ("unconstrained",re.compile(r"^\s*report_checks\s+-unconstrained\b")),
    ("negative_slack",re.compile(r"^\s*report_checks\s+--slack_max\s+-0\.01\b")),
    ("electrical_violators",re.compile(r"^\s*report_check_types\s+-max_slew\b")),
    ("parasitic_annotation",re.compile(r"^\s*report_parasitic_annotation\s+-report_unannotated\b")),
    ("check_setup",re.compile(r"^\s*check_setup\s+-verbose\b")),
]
REPORT_MAX=8*1024*1024
PATH_RX=re.compile(r"^\s*(Startpoint|Endpoint):\s*(.+)$")
SLACK_RX=re.compile(r"\bslack\s+\(?[A-Za-z ]*\)?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",re.I)
WARNING_RX=re.compile(r"(?i)(warning|error|unconstrained|no clock|no_clock|no input delay|no_input_delay|unconnected|loop)")
log=[]

def say(status,name,value):
    line=f"{status} | {name} | {value}"
    print(line,flush=True)
    log.append(line)

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while block:=f.read(1024*1024): h.update(block)
    return h.hexdigest()

def require(path, label):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} absent or symlink: {path}")

def parse_sections(path):
    require(path, "Post-route checks.rpt")
    if path.stat().st_size>REPORT_MAX:
        raise RuntimeError(f"Unexpected >8 MiB checks report: {path}")
    lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
    markers=[]
    for i,line in enumerate(lines):
        for label,pattern in HEADERS:
            if pattern.search(line):
                markers.append((i,label))
                break
    if len(markers)!=len(HEADERS) or [n for _,n in markers]!=[n for n,_ in HEADERS]:
        raise RuntimeError(f"Unexpected checks.rpt section headers: {path.name} / {markers}")
    out={}
    for j,(start,label) in enumerate(markers):
        end=markers[j+1][0] if j+1<len(markers) else len(lines)
        region=lines[start+1:end]
        # Remove nested report separators and repeated headings when evaluating
        # actual output, while preserving raw section for evidence.
        meaningful=[]
        for n,item in enumerate(region,start+2):
            t=item.strip()
            if t and not re.fullmatch(r"=+",t) and not re.match(r"=+ .+ Corner =+",t):
                meaningful.append({"line":n,"text":t[:280]})
        paths=[{"line":e["line"],"kind":match.group(1),"name":match.group(2)}
                for e in meaningful if (match:=PATH_RX.match(e["text"]))]
        no_paths=[e for e in meaningful if re.search("No paths found",e["text"],re.I)]
        warnings=[e for e in meaningful if WARNING_RX.search(e["text"])
                  and not e["text"].startswith("check_setup ")]
        slacks=[e for e in meaningful if SLACK_RX.search(e["text"])]
        out[label]={
            "command_line":start+1,
            "meaningful_line_count":len(meaningful),
            "no_paths_lines":no_paths,
            "startpoint_count":sum(p["kind"]=="Startpoint" for p in paths),
            "endpoint_count":sum(p["kind"]=="Endpoint" for p in paths),
            "path_examples":paths[:8],
            "warning_candidates":warnings[:45],
            "slack_lines":slacks[:12],
            "first_meaningful_lines":meaningful[:35],
        }
    return out

def main():
    print("===== ASIC STAGE 2J: UART UNCONSTRAINED VS NEGATIVE-SLACK AUDIT =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected normal non-root WSL Ubuntu user vaish")
    if not TEMP.is_dir():
        raise RuntimeError("G: Temp unavailable; cannot save audit")
    for label,path,expected in DIGESTS:
        require(path,label)
        if sha(path)!=expected:
            raise RuntimeError(f"{label} SHA256 mismatch; refusing audit")
        say("PASS",label,"SHA256 matches preserved baseline")
    for path in [CFG,METRICS,PROV]:
        require(path,path.name)
    if f"Git HEAD: {HEAD}" not in PROV.read_text(encoding="utf-8"):
        raise RuntimeError("Source provenance mismatch")
    say("PASS","Source provenance",HEAD)
    cfg=json.loads(CFG.read_text(encoding="utf-8"))
    metrics=json.loads(METRICS.read_text(encoding="utf-8"))
    if not isinstance(cfg,dict) or not isinstance(metrics,dict) or len(metrics)!=307:
        raise RuntimeError("Stage 2F resolved config or 307 metric keys unexpected")
    for key in ["PNR_SDC_FILE","SIGNOFF_SDC_FILE"]:
        p=cfg.get(key)
        if not isinstance(p,str):
            raise RuntimeError(f"Missing SDC config {key}")
        actual=Path(p)
        if not actual.is_absolute(): actual=BASE/actual
        if actual.resolve(strict=True)!=SDC.resolve(strict=True):
            raise RuntimeError(f"{key} does not point to pinned SDC")
    say("PASS","Applied SDC","Both PNR and signoff SDC paths resolved to pinned file")
    folder=[p for p in RUN.iterdir()
            if p.is_dir() and "openroad-stapostpnr" in p.name.lower()]
    if len(folder)!=1:
        raise RuntimeError(f"Expected 1 STA step dir, got {len(folder)}")
    corners=sorted(p for p in folder[0].iterdir() if p.is_dir())
    if len(corners)!=9:
        raise RuntimeError(f"Expected 9 PVT corner dirs, got {len(corners)}")
    proof=[]
    unconstrained_reported=0
    no_negative=0
    for corner in corners:
        blocks=parse_sections(corner/"checks.rpt")
        unconstrained=blocks["unconstrained"]
        negative=blocks["negative_slack"]
        name=corner.name
        # This check discriminates no-paths in unconstrained reporting
        # versus an intentionally empty negative-slack query.
        count_unconstrained=unconstrained["startpoint_count"]
        unconstrained_reported+=count_unconstrained
        if negative["no_paths_lines"]:
            no_negative+=1
        say("REPORT",name,
            f"unconstrained starts={count_unconstrained}; "
            f"slack<=-0.01 No paths found={len(negative['no_paths_lines'])}; "
            f"negative-slack starts={negative['startpoint_count']}")
        if count_unconstrained:
            say("REVIEW",name,
                f"Unconstrained timing paths in checks.rpt; first: "
                f"{unconstrained['path_examples'][0]['name'] if unconstrained['path_examples'] else 'see evidence'}")
        elif unconstrained["no_paths_lines"]:
            say("PASS",name+" unconstrained section","Explicit No paths found")
        else:
            say("REVIEW",name+" unconstrained section",
                f"No Startpoint and no No-paths marker; review {unconstrained['meaningful_line_count']} lines")
        checks=blocks["check_setup"]
        if checks["warning_candidates"]:
            say("REVIEW",name+" check_setup",
                f"{len(checks['warning_candidates'])} warning/unconstrained/loop keyword line(s); inspect JSON")
        for typ in ("setup","hold"):
            ws=metrics.get(f"timing__{typ}__ws__corner:{name}")
            wns=metrics.get(f"timing__{typ}__wns__corner:{name}")
            if ws is not None:
                say("TIMING",f"{name} {typ}","worst slack="+str(ws)+" ns, WNS="+str(wns)+" ns")
        # Additional clock propagation evidence in saved reports.
        clock=corner/"clock.rpt"
        unprop=corner/"unpropagated.rpt"
        clk_txt=clock.read_text(encoding="utf-8",errors="replace")[:25000] if clock.is_file() else None
        unprop_txt=unprop.read_text(encoding="utf-8",errors="replace")[:25000] if unprop.is_file() else None
        has_clock=bool(clk_txt and re.search(r"Clock:\s*uart_clk",clk_txt))
        propagated_lines=re.findall(r"(?m)^\s*Propagated:\s*.+",clk_txt) if clk_txt else []
        unprop_lines=[x.strip() for x in unprop_txt.splitlines()
                      if x.strip()] if unprop_txt else []
        if unprop_lines:
            say("REVIEW",name+" clock",f"Unpropagated clocks in saved report: {', '.join(unprop_lines[:3])}")
        proof.append({
            "corner":name,
            "sections":blocks,
            "per_corner_metrics":{k:v for k,v in metrics.items()
                                  if k.endswith(f"__corner:{name}") and
                                  (k.startswith("timing__") or k.startswith("design__max_"))},
            "clock_report_present":bool(clk_txt),
            "clock_uart_clk_present":has_clock,
            "clock_propagated_lines":propagated_lines[:8],
            "unpropagated_clocks":unprop_lines[:12],
        })
    say("INFO","Negative slack query",f"No paths found in {no_negative}/9 corners")
    say("INFO","Unconstrained path mentions",f"{unconstrained_reported} Startpoint entries across nine checks.rpt sections")
    if unconstrained_reported:
        say("REVIEW","STA constraint coverage","Unconstrained paths reported; cannot treat 0 WNS as full coverage")
    elif no_negative==9:
        say("INFO","STA path-group interpretation",
            "No paths found belongs to slack<=-0.01 report in all corners; separate unconstrained section still needs review")
    say("INFO","Signoff boundary",
        "Clock period/IO delays are provisional; physical CDC, PDK and shuttle approval remain open")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    jsonfile=TEMP/f"ASIC-Stage2J-UART-STA-Sections-{stamp}.json"
    textfile=TEMP/f"ASIC-Stage2J-UART-STA-Summary-{stamp}.txt"
    jsonfile.write_text(json.dumps({
        "scope":"READ-ONLY saved report section audit, NOT final STA signoff",
        "librelane_version":"3.0.17",
        "source_script":"librelane/scripts/openroad/sta/corner.tcl",
        "original_gds_sha256":DIGESTS[1][2],
        "constrained_gds_sha256":DIGESTS[0][2],
        "provisional_sdc_sha256":DIGESTS[2][2],
        "unconstrained_startpoint_mentions":unconstrained_reported,
        "negative_slack_empty_corners":no_negative,
        "corners":proof,
    },indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    say("PASS","Read-only Stage 2J extraction","9 PVT STA reports parsed; no design files changed")
    say("INFO","Full JSON evidence",str(jsonfile))
    say("INFO","Compact G: summary",str(textfile))
    textfile.write_text("\n".join(log)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 2J =====",flush=True)

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"FAIL | Stage 2J audit | {type(e).__name__}: {e}",file=sys.stderr)
        sys.exit(1)

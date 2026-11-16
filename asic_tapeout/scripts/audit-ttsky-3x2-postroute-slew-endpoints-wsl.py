#!/usr/bin/env python3
r"""Stage 3H — read-only OpenSTA post-route max-slew pin evidence audit.

Uses the already completed Stage 3E 3x2 TT SKY130 run. Does NOT rerun EDA,
change original GDS/SDC/RTL/PDK, invoke KLayout, fix timing, purchase tiles,
or run provider precheck. All new JSON/TXT reports go under G: Temp.
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
RUN=Path("/home/vaish/DevTools/LibreLane/ttsky_sky130_3x2_trial/run-46NnPce8/template/src/runs/tt-3x2-20261116-123932")
GDS=RUN/"final/gds/tt_um_vaish_uart.gds"
METRICS=RUN/"final/metrics.json"
MERGED=RUN.parent.parent/"config_merged.json"
GOLD2C=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
GOLD2F=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds")
GOLDSDC=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc")
PINNED=[
    (GDS,"4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","Stage 3E TT 3x2 final GDS"),
    (GOLD2C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Original Stage 2C GDS"),
    (GOLD2F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Original Stage 2F GDS"),
    (GOLDSDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Original Stage 2F SDC"),
]
CORNERS=("nom_ss_100C_1v60","max_ss_100C_1v60")
FLOAT=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
ROW=re.compile(r"^\s*(\S+)\s+("+FLOAT+r")\s+("+FLOAT+r")\s+("+FLOAT+r")(?:\s+\((VIOLATED|MET)\))?\s*$",re.I)
HEADER=re.compile(r"(?i)\bPin\b.*\bLimit\b.*\bSlew\b.*\bSlack\b")
RESULTS=[]
REPORTS={}

def output(kind,thing,detail):
    line=f"{kind} | {thing} | {detail}"
    RESULTS.append(line)
    print(line,flush=True)

def safe_file(p,label):
    if p.is_symlink() or not p.is_file():
        raise RuntimeError(f"{label} missing, non-file, or symlink: {p}")
    return p

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def check_immutables():
    for p,want,title in PINNED:
        safe_file(p,title)
        got=sha256(p)
        if got!=want:
            raise RuntimeError(f"{title} checksum changed: {got}")
        output("PASS",title,f"SHA256 {got[:16]}... preserved")
    cfg=json.loads(safe_file(MERGED,"Active trial configuration").read_text())
    if cfg.get("DESIGN_NAME")!="tt_um_vaish_uart" or \
       cfg.get("FP_DEF_TEMPLATE")!="dir::../tt/tech/sky130A/def/tt_block_3x2_pg.def" or \
       str(cfg.get("CLOCK_PERIOD")) not in ("100","100.0"):
        raise RuntimeError("Actual Stage3E 3x2 configuration differs")
    output("PASS","TT physical configuration","3x2 DEF, UART top and provisional 100ns clock")
    metric=json.loads(safe_file(METRICS,"Stage 3E final metrics").read_text())
    if len(metric)!=305 or metric.get("design__max_slew_violation__count")!=22:
        raise RuntimeError("Unexpected source run final slew metrics")
    for corner,expected in zip(CORNERS,(11,22)):
        value=metric.get("design__max_slew_violation__count__corner:"+corner)
        if value!=expected:
            raise RuntimeError(f"{corner} changed or missing: {value}")
        output("REVIEW","Saved max-slew "+corner,f"{value} violated check(s)")
    if cfg.get("RUN_KLAYOUT_DRC") not in (0,False):
        raise RuntimeError("Expected KLayout DRC-disabled source trial config changed")
    output("REVIEW","KLayout DRC","Disabled in saved run, not a DRC PASS")
    output("INFO","True stdcell area/utilization",
           f"{metric.get('design__instance__area__stdcell')} um2; "
           f"{100*metric.get('design__instance__utilization__stdcell',0):.3f}% "
           "(not 96.53% physical-only-filled instance area)")
    return metric

def extract_max_slew(text):
    """Parse OpenSTA max slew Pin/Limit/Slew/Slack section; no guessed pins."""
    lines=text.splitlines()
    all_rows=[]
    found_headers=0
    for i,line in enumerate(lines):
        if line.strip().lower()!="max slew":
            continue
        header_idx=None
        for j in range(i+1,min(i+14,len(lines))):
            if HEADER.search(lines[j]):
                header_idx=j
                break
            if re.search(r"(?i)^\s*max (?:fanout|capacitance|cap|slew violation count)\b",lines[j]):
                break
        if header_idx is None:
            continue
        found_headers+=1
        for j in range(header_idx+1,min(header_idx+1200,len(lines))):
            s=lines[j].strip()
            if re.match(r"(?i)^max (?:capacitance|cap|fanout|slew violation count)\b",s) or \
               re.match(r"^={8,}",s):
                break
            m=ROW.match(lines[j])
            if not m:
                continue
            pin,limit,slew,slack,status=m.groups()
            sl=Decimal(slack)
            if (status or "").upper()=="VIOLATED" or sl<0:
                all_rows.append({
                    "pin":pin,"limit":str(Decimal(limit)),
                    "slew":str(Decimal(slew)),"slack":str(sl),
                    "status":status or "NEGATIVE_SLACK","line":j+1,
                })
    uniq={}
    for row in all_rows:
        pin=row["pin"]
        if pin not in uniq or Decimal(row["slack"])<Decimal(uniq[pin]["slack"]):
            uniq[pin]=row
    return sorted(uniq.values(),key=lambda r:Decimal(r["slack"])),found_headers

def parser_selftest():
    fixture="""max slew

Pin                     Limit   Slew   Slack
--------------------------------------------
_8_44/A                 80.00 330.31 -250.31 (VIOLATED)
_8_46/A                 80.00 309.18 -229.18 (VIOLATED)
max fanout
"""
    rows,headers=extract_max_slew(fixture)
    if headers!=1 or len(rows)!=2 or rows[0]["pin"]!="_8_44/A" or rows[0]["slack"]!="-250.31":
        raise RuntimeError("OpenSTA max-slew parser self-test failed")
    output("PASS","OpenSTA row parser self-test","Pin/Limit/Slew/Slack/VIOLATED lines parsed")

def inspect_saved_reports():
    report_files=[]
    for p in RUN.rglob("checks.rpt"):
        if p.is_symlink() or not p.is_file():
            continue
        if "openroad" not in str(p):
            continue
        if p.stat().st_size>8*1024*1024:
            continue
        report_files.append(p)
    if len(report_files)>150:
        raise RuntimeError("Unexpected >150 saved OpenSTA checks.rpt files")
    output("INFO","Saved OpenSTA checks.rpt files",len(report_files))
    found=[]
    for p in sorted(report_files):
        relative=p.relative_to(RUN)
        corner=next((c for c in CORNERS if c in relative.parts),None)
        if not corner:
            continue
        stage=str(relative.parts[0]) if relative.parts else "unknown"
        try:
            content=p.read_text(encoding="utf-8",errors="replace")
        except OSError:
            continue
        rows,header_count=extract_max_slew(content)
        entry={
            "path":str(p),"stage":stage,"corner":corner,
            "section_headers":header_count,
            "violator_rows":rows,
            "violator_pins_found":len(rows),
        }
        found.append(entry)
    REPORTS["all_slew_reports"]=found
    if not found:
        output("REVIEW","Saved OpenSTA section discovery","No SS-corner checks.rpt matched. Do not invent failing pins.")
        return
    grouped={}
    for corner in CORNERS:
        entries=[e for e in found if e["corner"]==corner]
        def stage_num(e):
            m=re.match(r"(\d+)",e["stage"])
            return int(m.group(1)) if m else -1
        late=[e for e in entries if re.search(r"postpnr|postroute|post-route",e["stage"],re.I)]
        pool=late if late else entries
        if not pool:
            output("REVIEW","Saved slew report "+corner,"No matching report")
            continue
        selected=max(pool,key=stage_num)
        grouped[corner]=selected
        label="POSTROUTE" if late else "LATEST SAVED (NOT VERIFIED POSTROUTE)"
        output("REPORT",corner,
               f"{label}; stage={selected['stage']}; "
               f"{selected['violator_pins_found']} named violating pins; "
               f"max-slew sections={selected['section_headers']}")
        output("INFO","OpenSTA source file",selected["path"])
        for row in selected["violator_rows"][:10]:
            output("PIN","max slew "+corner,
                   f"{row['pin']} | limit={row['limit']} slew={row['slew']} "
                   f"slack={row['slack']} ({row['status']})")
        if not selected["violator_rows"]:
            output("REVIEW","Exact failing pin names",
                   "Report did not expose parseable max-slew rows; metric violation count is still nonzero")
        elif len(selected["violator_rows"])< (11 if corner==CORNERS[0] else 22):
            output("REVIEW","Pin-list coverage",
                   "Fewer named violators than saved metric count; report may limit displayed rows")
    REPORTS["selected_snapshots"]=grouped
    output("INFO","Prior-route comparison",f"{len(found)} saved SS-corner reports indexed in G: JSON")

def main():
    print("===== ASIC STAGE 3H: TT 3X2 SAVED POSTROUTE SLEW PIN AUDIT =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root WSL Ubuntu user vaish")
    if not TEMP.is_dir() or not RUN.is_dir():
        raise RuntimeError("G: Temp or exact preserved Stage3E run missing")
    parser_selftest()
    m=check_immutables()
    inspect_saved_reports()
    output("REVIEW","Physical signoff",
           "Max-slew remains nonzero; KLayout DRC skipped; no provider precheck or approved clock/IO constraints")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    details=TEMP/f"ASIC-Stage3H-TTSKY-3x2-PostRoute-Slew-{stamp}.json"
    summary=TEMP/f"ASIC-Stage3H-TTSKY-3x2-Summary-{stamp}.txt"
    details.write_text(json.dumps({
        "scope":"Read-only saved OpenSTA slew pins, not active STA repair or provider signoff",
        "run":str(RUN),"pinned_gds_sha256":PINNED[0][1],
        "max_slew_count":m["design__max_slew_violation__count"],
        "stdcell_area":m.get("design__instance__area__stdcell"),
        "stdcell_utilization":m.get("design__instance__utilization__stdcell"),
        "saved_checks":REPORTS,
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    output("PASS","Stage 3H read-only analysis","All original GDSII, SDC, PDK and RTL unchanged")
    output("INFO","Detailed G: evidence",str(details))
    output("INFO","Compact G: summary",str(summary))
    summary.write_text("\n".join(RESULTS)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3H =====",flush=True)

if __name__=="__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL | Stage 3H | {type(error).__name__}: {error}",file=sys.stderr,flush=True)
        sys.exit(1)

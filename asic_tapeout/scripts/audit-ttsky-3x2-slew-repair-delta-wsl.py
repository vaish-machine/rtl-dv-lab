#!/usr/bin/env python3
r"""ASIC Stage 3N: read-only Stage 3M vs 3E post-route slew diagnostics.

Inspect the original and repaired 3x2 Tiny Tapeout SKY130 local GDSII,
the two exact final LibreLane metrics files, saved postroute OpenSTA
max-slew reports, and mapped gate-level netlists. Compare the remaining
violating pins and their named nets, without equating renamed instance
IDs across separate physical flows. No EDA execution, no RTL/GDS/SDC/
PDK modifications, no KLayout invocation, provider CI, or submission.
Only new evidence JSON/TXT under G:\C-Drive-Backup-PreReset\Temp.
"""
from __future__ import annotations

from collections import defaultdict
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
TOOLROOT=Path("/home/vaish/DevTools/LibreLane")
BASE=TOOLROOT/"ttsky_sky130_3x2_trial/run-46NnPce8/template/src/runs/tt-3x2-20261116-123932"
TRIAL=TOOLROOT/"ttsky_sky130_3x2_slew_repair_trial/run-dnsp_mu6/src/runs/slewfix-3x2-20261118-105720"
WORK=TRIAL.parent.parent.parent
GDS_NAME="tt_um_vaish_uart.gds"
BASE_GDS=BASE/"final/gds"/GDS_NAME
TRIAL_GDS=TRIAL/"final/gds"/GDS_NAME
OLD2C=TOOLROOT/"uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
OLD2F=TOOLROOT/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
OLD_SDC=TOOLROOT/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc"
PINNED=(
    (BASE_GDS,"4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","Original Stage 3E TT 3x2 GDS"),
    (TRIAL_GDS,"a095ed4615d65d2a4a557c4a14c7914ca6717bd98a8251a742128a0f3fe5a166","Stage 3M repaired TT 3x2 GDS"),
    (OLD2C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Stage 2C original GDS"),
    (OLD2F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Stage 2F original GDS"),
    (OLD_SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Stage 2F provisional SDC"),
)
CORNERS=("nom_ss_100C_1v60","max_ss_100C_1v60")
BASELINE_3I=TEMP/"ASIC-Stage3I-TTSKY-3x2-Net-Driver-20261116-171214.json"
CELL=re.compile(r"(?ms)^[ \t]*(?P<type>sky130_[A-Za-z0-9_$]+)[ \t]+(?P<inst>\\?[A-Za-z0-9_$./:-]+)[ \t]*\((?P<body>.*?)\)[ \t]*;")
PIN=re.compile(r"\.([A-Za-z_][A-Za-z_0-9$]*)\s*\(\s*([^()]*?)\s*\)",re.S)
FLOAT=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
ROW=re.compile(r"^\s*(\S+)\s+("+FLOAT+r")\s+("+FLOAT+r")\s+("+FLOAT+r")(?:\s+\((VIOLATED|MET)\))?\s*$",re.I)
HEADER=re.compile(r"(?i)\bPin\b.*\bLimit\b.*\bSlew\b.*\bSlack\b")
OUT={"X","Y","Z","ZN","Q","QN","Q_N","IQ","IQ_N","CO","COUT","SUM","CLKOUT"}
LINES=[]
EVIDENCE={"scope":"Read-only saved Stage3M vs Stage3E comparison; no provider signoff"}

def emit(status,label,value):
    line=f"{status} | {label} | {value}"
    print(line,flush=True)
    LINES.append(line)

def file(path,name,limit=48*1024*1024):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{name}: file missing or symlink: {path}")
    if path.stat().st_size>limit:
        raise RuntimeError(f"{name}: larger than expected")
    return path

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def json_file(path,label):
    d=json.loads(file(path,label).read_text(encoding="utf-8"))
    if not isinstance(d,dict):
        raise RuntimeError(f"{label} did not contain an object")
    return d

def normalize(value):
    return re.sub(r"\s+","",value.strip().lstrip("\\")).rstrip(";")

def cells_for(run):
    path=file(run/"final/nl/tt_um_vaish_uart.nl.v","Saved functional netlist")
    content=path.read_text(encoding="utf-8",errors="replace")
    cells={}
    nets=defaultdict(list)
    for m in CELL.finditer(content):
        inst=normalize(m.group("inst"))
        ports={pin:normalize(net) for pin,net in PIN.findall(m.group("body"))}
        if ports:
            cells[inst]={"type":m.group("type"),"ports":ports}
            for port,net in ports.items():
                if not re.match(r"^\d+'[bdho]",net,re.I):
                    nets[net].append({"inst":inst,"port":port,"type":m.group("type")})
    return path,cells,nets

def parser(text):
    lines=text.splitlines()
    rows=[]
    for idx,line in enumerate(lines):
        if line.strip().lower()!="max slew":
            continue
        header=None
        for j in range(idx+1,min(idx+15,len(lines))):
            if HEADER.search(lines[j]):
                header=j
                break
        if header is None:
            continue
        for j in range(header+1,min(header+1000,len(lines))):
            t=lines[j].strip()
            if re.match(r"(?i)^max (?:fanout|capacitance|cap|slew violation count)\b",t) or re.match(r"^={8,}",t):
                break
            m=ROW.match(lines[j])
            if m is None:
                continue
            pin,limit,slew,slack,flag=m.groups()
            try:
                sl=Decimal(slack)
            except Exception:
                continue
            if sl<0 or (flag or "").upper()=="VIOLATED":
                rows.append({"pin":pin,"limit":limit,"slew":slew,"slack":slack,"line":j+1})
    best={}
    for row in rows:
        p=row["pin"]
        if p not in best or Decimal(row["slack"])<Decimal(best[p]["slack"]):
            best[p]=row
    return sorted(best.values(),key=lambda e:Decimal(e["slack"]))

def test():
    text="""max slew

 Pin Limit Slew Slack
 _320_/C1 0.750000 0.802130 -0.052130 (VIOLATED)
 fanout27/X 0.750000 0.801999 -0.051999 (VIOLATED)
 max fanout
"""
    r=parser(text)
    if len(r)!=2 or r[0]["pin"]!="_320_/C1":
        raise RuntimeError("OpenSTA report parser self-test failed")
    emit("PASS","OpenSTA max-slew parser fixture","Pin, transition, limit and negative slack")

def verify():
    for path,expected,label in PINNED:
        file(path,label)
        actual=sha(path)
        if actual!=expected:
            raise RuntimeError(f"{label} changed SHA256 {actual}")
        emit("PASS",label,actual[:16]+"... preserved")
    m0=json_file(BASE/"final/metrics.json","Stage 3E metrics")
    m1=json_file(TRIAL/"final/metrics.json","Stage 3M metrics")
    if len(m0)!=305 or len(m1)!=307:
        raise RuntimeError("Unexpected baseline/trial metric counts")
    if m0.get("design__max_slew_violation__count")!=22 or m1.get("design__max_slew_violation__count")!=11:
        raise RuntimeError("Unexpected Stage3E/3M aggregate max-slew counts")
    for corner,old,new in [(CORNERS[0],11,11),(CORNERS[1],22,11)]:
        key="design__max_slew_violation__count__corner:"+corner
        if m0.get(key)!=old or m1.get(key)!=new:
            raise RuntimeError(f"Unexpected saved {corner} violation counts")
    for key in ("route__drc_errors","magic__drc_error__count",
                "design__lvs_error__count","timing__setup_vio__count",
                "timing__hold_vio__count","klayout__drc_error__count"):
        if m1.get(key)!=0:
            raise RuntimeError(f"Trial {key} expected 0, observed {m1.get(key)}")
    provenance=json_file(WORK/"provenance.json","Stage3M isolated provenance")
    compare=json_file(WORK/"comparison.json","Stage3M saved comparison")
    if provenance.get("baseline_GDS_SHA256")!=PINNED[0][1] or \
       compare.get("baseline_gds_sha256")!=PINNED[0][1] or \
       compare.get("trial_gds_sha256")!=PINNED[1][1]:
        raise RuntimeError("Stage3M provenance or comparison hashes inconsistent")
    cfg=json_file(WORK/"src/config_3m.json","Stage3M trial configuration")
    if cfg.get("RUN_KLAYOUT_DRC") not in (1,True) or \
       str(cfg.get("CLOCK_PERIOD")) not in ("100","100.0") or \
       cfg.get("DESIGN_REPAIR_MAX_SLEW_PCT")!=30:
        raise RuntimeError("Stage3M copied repair configuration unexpected")
    emit("PASS","Stage3M pinned source and configuration","100ns clock, 30% repair margin, KLayout enabled, no RTL rewrite")
    for k in ("design__max_slew_violation__count","route__drc_errors","magic__drc_error__count",
              "klayout__drc_error__count","design__lvs_error__count",
              "timing__setup_vio__count","timing__hold_vio__count",
              "design__instance__area__stdcell","design__instance__utilization__stdcell"):
        emit("METRIC",k,f"Stage3E={m0.get(k,'UNREPORTED')}; Stage3M={m1.get(k,'UNREPORTED')}")
    EVIDENCE["metrics"]={k:{"baseline":m0.get(k),"trial":m1.get(k)}
                         for k in set(m0)|set(m1) if "slew" in k or k in ("klayout__drc_error__count","design__instance__area__stdcell")}
    return m0,m1

def report_for(run,corner):
    matches=[]
    for p in run.rglob("checks.rpt"):
        if p.is_symlink() or not p.is_file() or p.stat().st_size>8*1024*1024:
            continue
        rel=p.relative_to(run)
        if corner in rel.parts and "stapostpnr" in str(rel.parts[0]).lower():
            m=re.match(r"(\d+)-",rel.parts[0])
            priority=int(m.group(1)) if m else -1
            matches.append((priority,p))
    if not matches:
        emit("REVIEW","Postroute OpenSTA report "+corner,"No saved stapostpnr checks.rpt found")
        return None,[]
    _,selected=max(matches,key=lambda item:item[0])
    entries=parser(selected.read_text(encoding="utf-8",errors="replace"))
    emit("REPORT",corner,f"{len(entries)} named violating pins from {selected}")
    return selected,entries

def assign_nets(rows,cells):
    result=[]
    for r in rows:
        pin=r["pin"]
        if "/" not in pin:
            result.append(r|{"net":None,"cell_type":None,"reason":"no instance/pin separator"})
            continue
        instance,port=pin.rsplit("/",1)
        name=normalize(instance)
        cell=cells.get(name)
        if cell is None:
            result.append(r|{"net":None,"cell_type":None,"reason":"instance not in saved netlist"})
            continue
        result.append(r|{"net":cell["ports"].get(port),
                         "cell_type":cell["type"],
                         "reason":None if port in cell["ports"] else "named pin absent"})
    return result

def compare():
    old_path,old_cells,_=cells_for(BASE)
    new_path,new_cells,new_nets=cells_for(TRIAL)
    emit("PASS","Saved signal-connected netlists",
         f"baseline {len(old_cells)} cells; repaired {len(new_cells)} cells")
    emit("INFO","New final netlist",str(new_path))
    prior=json_file(BASELINE_3I,"Stage3I original net group evidence")
    if prior.get("gds_sha256")!=PINNED[0][1]:
        raise RuntimeError("Original Stage3I net group evidence references different GDS")
    old_map={r["pin"]:r["net"] for r in prior.get("mapped",{}).get("mapped_sinks",[])}
    if len(old_map)!=22 or set(old_map.values())!={"net16","net27"}:
        raise RuntimeError("Baseline 22-pin grouping not found in Stage3I evidence")
    EVIDENCE["original_net_groups"]={k:sum(n==k for n in old_map.values()) for k in ("net16","net27")}
    evidence={}
    for corner in CORNERS:
        old_file,old_rows=report_for(BASE,corner)
        new_file,new_rows=report_for(TRIAL,corner)
        grp=defaultdict(list)
        if new_file is not None:
            for r in assign_nets(new_rows,new_cells):
                grp[r["net"] or "UNRESOLVED"].append(r)
        exact_old={x["pin"] for x in old_rows}
        exact_new={x["pin"] for x in new_rows}
        persist=sorted(exact_old&exact_new)
        appeared=sorted(exact_new-exact_old)
        vanished=sorted(exact_old-exact_new)
        emit("INFO","Pin-name comparison "+corner,
             f"shared names={len(persist)}, old-only={len(vanished)}, new-only={len(appeared)}; names may change after resynthesis")
        for net,pins in sorted(grp.items(),key=lambda x:-len(x[1])):
            emit("NET","Trial violations "+corner,
                 f"{net}: {len(pins)} named checks; sample pins="+", ".join(x["pin"] for x in pins[:5]))
        for r in sorted(assign_nets(new_rows,new_cells),key=lambda x:Decimal(x["slack"]))[:12]:
            emit("PIN","Remaining slew "+corner,
                 f"{r['pin']} net={r.get('net') or 'UNRESOLVED'} limit={r['limit']}ns "
                 f"slew={r['slew']}ns slack={r['slack']}ns")
        evidence[corner]={
            "baseline_report":str(old_file) if old_file else None,
            "trial_report":str(new_file) if new_file else None,
            "baseline_rows":old_rows,"trial_rows":assign_nets(new_rows,new_cells),
            "by_trial_net":{k:len(v) for k,v in grp.items()},
            "old_new_pin_intersection":persist,
            "only_in_baseline_by_name":vanished,
            "only_in_trial_by_name":appeared
        }
    EVIDENCE["postroute_slew"]=evidence
    if all(evidence[c]["trial_report"] for c in CORNERS):
        emit("PASS","Stage3M final postroute slew report audit","Both SS corner reports located; pinned metric counts still apply")
        for corner,n in [(CORNERS[0],11),(CORNERS[1],11)]:
            count=len(evidence[corner]["trial_rows"])
            if count!=n:
                emit("REVIEW","Per-pin report coverage "+corner,
                     f"found {count} rows vs {n} final metric violations; report may truncate or parser may miss rows")
    else:
        emit("REVIEW","Stage3M postroute report coverage",
             "One or more final SS reports unavailable; no per-pin cause conclusion")
    emit("REVIEW","Attribution caution","Net and pin names may change across distinct synth/PnR runs; confirm sources before a targeted ECO")

def main():
    print("===== ASIC STAGE 3N: TT 3X2 POST-REPAIR SLEW PIN COMPARISON =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root Ubuntu user vaish")
    if not TEMP.is_dir() or not BASE.is_dir() or not TRIAL.is_dir():
        raise RuntimeError("Expected G: Temp and saved Stage3E/Stage3M physical runs")
    test()
    verify()
    compare()
    emit("REVIEW","Local signoff","11 max-slew violations remain; production clock/IO/CDC and official provider precheck OPEN")
    now=datetime.now().strftime("%Y%m%d-%H%M%S")
    out=TEMP/f"ASIC-Stage3N-TTSKY-3x2-PostRepair-Slew-{now}.json"
    summary=TEMP/f"ASIC-Stage3N-TTSKY-3x2-Summary-{now}.txt"
    EVIDENCE["original_GDS_sha256"]=PINNED[0][1]
    EVIDENCE["trial_GDS_sha256"]=PINNED[1][1]
    out.write_text(json.dumps(EVIDENCE,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    emit("PASS","Stage 3N read-only audit","All original and trial GDS, SDC, RTL and PDK left unchanged")
    emit("INFO","Detailed G: evidence",str(out))
    emit("INFO","Compact G: summary",str(summary))
    summary.write_text("\n".join(LINES)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3N =====",flush=True)

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print(f"FAIL | Stage 3N | {type(e).__name__}: {e}",file=sys.stderr,flush=True)
        sys.exit(1)

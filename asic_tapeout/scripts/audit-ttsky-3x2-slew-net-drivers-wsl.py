#!/usr/bin/env python3
r"""ASIC Stage 3I: read-only trace of saved SS max-slew sink pins to gate nets.

Inputs: exact Stage 3H saved JSON and exact Stage 3E 3x2 PnR run.
No EDA process, synthesis, placement, route, OpenROAD edits, KLayout,
PDK writes, GDS changes, new provider Actions or submission.
Evidence under G:\C-Drive-Backup-PreReset\Temp exclusively.
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
STAGE3H=TEMP/"ASIC-Stage3H-TTSKY-3x2-PostRoute-Slew-20261116-161853.json"
RUN=Path("/home/vaish/DevTools/LibreLane/ttsky_sky130_3x2_trial/run-46NnPce8/template/src/runs/tt-3x2-20261116-123932")
GDS=RUN/"final/gds/tt_um_vaish_uart.gds"
METRICS=RUN/"final/metrics.json"
GOLD2C=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
GOLD2F=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds")
GOLDSDC=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc")
PINS=[
    (GDS,"4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","Stage 3E 3x2 final GDS"),
    (GOLD2C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Stage 2C original GDS"),
    (GOLD2F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Stage 2F original GDS"),
    (GOLDSDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Stage 2F original SDC"),
]
CORNERS=("nom_ss_100C_1v60","max_ss_100C_1v60")
INST=re.compile(r"(?ms)^[ \t]*(?P<cell>sky130_[A-Za-z0-9_$]+)[ \t]+(?P<inst>\\?[A-Za-z0-9_$./:-]+)[ \t]*\((?P<body>.*?)\)[ \t]*;")
CONN=re.compile(r"\.([A-Za-z_][A-Za-z_0-9$]*)\s*\(\s*([^()]*?)\s*\)",re.S)
OUTPUT_NAMES={"X","Y","Z","ZN","Q","Q_N","QN","IQ","IQ_N","CLKOUT","CO","COUT","SUM","S"}
LINES=[]

def show(status,label,detail):
    s=f"{status} | {label} | {detail}"
    print(s,flush=True)
    LINES.append(s)

def check_file(p,desc):
    if p.is_symlink() or not p.is_file():
        raise RuntimeError(f"{desc} missing or symlink: {p}")
    return p

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def get_json(path,desc):
    check_file(path,desc)
    if path.stat().st_size>15*1024*1024:
        raise RuntimeError(f"Unexpected oversized {desc}")
    return json.loads(path.read_text(encoding="utf-8"))

def canon(name):
    return re.sub(r"\s+","",name.strip().lstrip("\\")).rstrip(";")

def parse_netlist(text):
    cells={}
    for m in INST.finditer(text):
        inst=canon(m.group("inst"))
        ports={name:canon(net) for name,net in CONN.findall(m.group("body"))}
        if ports:
            cells[inst]={"type":m.group("cell"),"ports":ports}
    return cells

def selftest():
    fixture=r"""
module test;
  sky130_fd_sc_hd__buf_2 fanout26 (
      .A(_wire_5), .X(_wide_42)
  );
  sky130_fd_sc_hd__a21oi_1 _320_ (
      .A1(_net_1), .C1(_wide_42), .Y(_out_2)
  );
  sky130_fd_sc_hd__nand2_1 \_201_  (
      .A1(_wide_42), .B1(_net_3), .Y(_out_1)
  );
endmodule
"""
    cells=parse_netlist(fixture)
    assert set(("fanout26","_320_","_201_")).issubset(cells),cells
    assert cells["_320_"]["ports"]["C1"]=="_wide_42",cells["_320_"]
    assert cells["fanout26"]["ports"]["X"]=="_wide_42"
    assert cells["_201_"]["ports"]["A1"]=="_wide_42"
    show("PASS","Cell/port connection parser self-test",
         "Escaped instances, multi-line standard cells, shared nets")

def verify_input():
    for p,want,desc in PINS:
        check_file(p,desc)
        got=sha(p)
        if got!=want:
            raise RuntimeError(f"{desc} unexpected SHA256 {got}")
        show("PASS",desc,f"SHA256 {got[:16]}... preserved")
    m=get_json(METRICS,"Stage 3E final metrics")
    if len(m)!=305 or m.get("design__max_slew_violation__count")!=22:
        raise RuntimeError("Unexpected Stage 3E metrics")
    report=get_json(STAGE3H,"Saved Stage 3H pinned max-slew evidence")
    snapshots=report.get("saved_checks",{}).get("selected_snapshots",{})
    expected={"nom_ss_100C_1v60":11,"max_ss_100C_1v60":22}
    for corner,count in expected.items():
        snap=snapshots.get(corner)
        if not isinstance(snap,dict) or "stapostpnr" not in snap.get("stage",""):
            raise RuntimeError(f"Stage3H postroute source missing for {corner}")
        rows=snap.get("violator_rows",[])
        if len(rows)!=count:
            raise RuntimeError(f"Stage3H saved {corner} pin count unexpected: {len(rows)}")
        if m.get("design__max_slew_violation__count__corner:"+corner)!=count:
            raise RuntimeError(f"Metrics/{corner} differ")
        show("PASS","Pinned Stage3H postroute "+corner,
             f"{len(rows)} genuine OpenSTA violated pins")
    return report,snapshots

def candidates():
    items=[]
    for p in RUN.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        if p.suffix.lower() not in (".v",".vg",".sv"):
            continue
        if p.stat().st_size>18*1024*1024:
            continue
        if "tt" in p.relative_to(RUN).parts and "src" in p.relative_to(RUN).parts:
            continue
        items.append(p)
    if len(items)>200:
        raise RuntimeError("Unexpected >200 saved Verilog netlist candidates; no files changed")
    return items

def netlist_choice(targets):
    scored=[]
    for p in candidates():
        content=p.read_text(encoding="utf-8",errors="replace")
        cells=parse_netlist(content)
        matched=[name for name in targets if name in cells]
        if not matched:
            continue
        weight=(10 if "/final/nl/" in str(p) else 0)+(2 if "routed" in p.name.lower() else 0)
        scored.append({"path":str(p),"matched":matched,
                       "total_cells":len(cells),"weight":weight,"cells":cells})
    scored.sort(key=lambda x:(len(x["matched"]),x["weight"],x["total_cells"]),reverse=True)
    for info in scored[:6]:
        show("CANDIDATE","Mapped standard-cell netlist",
             f"{len(info['matched'])}/{len(targets)} failing instances; "
             f"{info['total_cells']} cells; {info['path']}")
    return scored

def analyze(snapshot,choice):
    actual_pins=sorted({r["pin"] for c in CORNERS for r in snapshot[c]["violator_rows"]})
    cells=choice["cells"]
    nets=defaultdict(list)
    for instance,desc in cells.items():
        for port,net in desc["ports"].items():
            if not net or net.startswith(("1'b","1'h","1'd")):
                continue
            nets[net].append({"instance":instance,"port":port,"cell_type":desc["type"]})
    grouped=defaultdict(list)
    missing=[]
    sinks=[]
    for pin in actual_pins:
        if "/" not in pin:
            missing.append({"pin":pin,"reason":"no instance/pin separator"})
            continue
        instance,port=pin.rsplit("/",1)
        instance=canon(instance)
        desc=cells.get(instance)
        if not desc:
            missing.append({"pin":pin,"reason":"instance absent from selected saved netlist"})
            continue
        net=desc["ports"].get(port)
        if net is None:
            missing.append({"pin":pin,"reason":"pin absent in selected cell instance ports","cell_type":desc["type"]})
            continue
        sinks.append({"pin":pin,"net":net,"instance":instance,
                      "port":port,"cell_type":desc["type"]})
        grouped[net].append(pin)
    by_corner={c:{r["pin"]:r for r in snapshot[c]["violator_rows"]} for c in CORNERS}
    evidence=[]
    for net,pins in sorted(grouped.items(),key=lambda kv:-len(kv[1])):
        links=nets[net]
        potential=[f"{x['instance']}/{x['port']} ({x['cell_type']})"
                   for x in links if x["port"].upper() in OUTPUT_NAMES]
        record={"net":net,"violator_pins":pins,
                "connected_cell_pins":links,"output_port_candidates":potential}
        evidence.append(record)
        show("NET","Shared candidate drive net",
             f"{net} | {len(pins)}/{len(actual_pins)} failing pins; "
             f"{len(links)} connected cell ports; possible drivers={potential[:4] or 'NOT CLASSIFIED'}")
        for pin in pins[:12]:
            m=by_corner[CORNERS[1]].get(pin)
            if not m:
                m=by_corner[CORNERS[0]].get(pin)
            show("PIN","Mapped max-slew sink",
                 f"{pin} -> {net} | {m['slew']} ns transition, "
                 f"{m['limit']} ns limit, slack {m['slack']} ns")
    show("INFO","Failing pins mapped to gate netlist",
         f"{len(sinks)}/{len(actual_pins)} unique pin names")
    if missing:
        show("REVIEW","Unresolved pin mappings",
             f"{len(missing)} names; first names="+
             ", ".join(f"{r['pin']} ({r['reason']})" for r in missing[:5]))
    if grouped and len(grouped)==1:
        show("HYPOTHESIS","Common high fanout source",
             "All mapped violating pins share one named gate net; "
             "verify actual OpenDB driver, capacitance and fanout before editing")
    else:
        show("REVIEW","Driver diagnosis",
             "Connected-net grouping is static; exact drive capabilities/loads require OpenDB/STA")
    return {"connections":evidence,"unresolved":missing,"mapped_sinks":sinks}

def main():
    print("===== ASIC STAGE 3I: TT 3X2 SLEW NET DRIVER TRACE =====",flush=True)
    if os.geteuid()==0 or getpass.getuser()!="vaish":
        raise RuntimeError("Expected non-root WSL Ubuntu vaish")
    if not TEMP.is_dir() or not RUN.is_dir():
        raise RuntimeError("Expected G: Temp and saved TT Stage3E run")
    selftest()
    report,snapshots=verify_input()
    target={r["pin"].rsplit("/",1)[0].lstrip("\\")
            for c in CORNERS for r in snapshots[c]["violator_rows"]}
    scored=netlist_choice(target)
    info={"scope":"Static saved gate-net mapping; no ODB electrical proof or timing repair",
          "stage3h_evidence":str(STAGE3H),"run":str(RUN),
          "gds_sha256":PINS[0][1],"target_instances":sorted(target)}
    if scored:
        best=scored[0]
        show("PASS","Best saved mapped netlist",
             f"{best['path']} ({len(best['matched'])}/{len(target)} target instances)")
        info["chosen_netlist"]=best["path"]
        info["chosen_netlist_sha256"]=sha(Path(best["path"]))
        info["mapped"]=analyze(snapshots,best)
        info["candidate_files"]=[{"path":x["path"],"matched":len(x["matched"]),
                                 "cells":x["total_cells"]} for x in scored]
    else:
        show("REVIEW","Saved gate netlist",
             "No standard-cell instance match found in available Verilog; no driver/net claim")
        info["available_verilog"]=[str(x) for x in candidates()]
    show("REVIEW","Physical signoff",
         "22 slow-corner max-slew violations OPEN; KLayout DRC disabled; "
         "provider GDS/precheck, clock/IO and CDC still OPEN")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    detailed=TEMP/f"ASIC-Stage3I-TTSKY-3x2-Net-Driver-{stamp}.json"
    summary=TEMP/f"ASIC-Stage3I-TTSKY-3x2-Summary-{stamp}.txt"
    detailed.write_text(json.dumps(info,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    show("PASS","Read-only Stage 3I",
         "Original GDSII/SDC/PDK/RTL unchanged; no EDA flow executed")
    show("INFO","Detailed G: evidence",str(detailed))
    show("INFO","Compact G: summary",str(summary))
    summary.write_text("\n".join(LINES)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3I =====",flush=True)

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print(f"FAIL | Stage 3I | {type(e).__name__}: {e}",file=sys.stderr,flush=True)
        sys.exit(1)

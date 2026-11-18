#!/usr/bin/env python3
r"""ASIC Stage 3L: read-only source-cell input & max-slew evidence audit.

Read the exact successful Stage3K JSON, prior OpenSTA Stage3H postroute
violation records and the preserved SKY130 mapped final gate netlist.
Inspect input1 and _297_ actual input pins, associated upstream driver
candidates, and both slew-violating branches. Never guess clock ancestry
or perform a buffer ECO, synthesis, place/route, KLayout or provider action.
All new JSON/TXT files go to G:-backed /mnt/g/.../Temp only.
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
RUN=Path("/home/vaish/DevTools/LibreLane/ttsky_sky130_3x2_trial/run-46NnPce8/template/src/runs/tt-3x2-20261116-123932")
NETLIST=RUN/"final/nl/tt_um_vaish_uart.nl.v"
GDS=RUN/"final/gds/tt_um_vaish_uart.gds"
METRICS=RUN/"final/metrics.json"
THREE_K=TEMP/"ASIC-Stage3K-TTSKY-3x2-Upstream-Source-20261118-102531.json"
THREE_H=TEMP/"ASIC-Stage3H-TTSKY-3x2-PostRoute-Slew-20261116-161853.json"
TWO_C=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
TWO_F=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds")
SDC=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc")
PINS=(
    (GDS,"4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","Original TT 3x2 final GDS"),
    (TWO_C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Original Stage 2C GDS"),
    (TWO_F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Original Stage 2F GDS"),
    (SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Original provisional Stage 2F SDC"),
)
CELL=re.compile(r"(?ms)^[ \t]*(?P<type>sky130_[A-Za-z0-9_$]+)[ \t]+(?P<name>\\?[A-Za-z0-9_$./:-]+)[ \t]*\((?P<body>.*?)\)[ \t]*;")
PORT=re.compile(r"\.([A-Za-z_][A-Za-z_0-9$]*)\s*\(\s*([^()]*?)\s*\)",re.S)
ALIAS=re.compile(r"(?m)^[ \t]*assign[ \t]+([^=;]+?)\s*=\s*([^;]+);")
SIMPLE=re.compile(r"^\\?[A-Za-z_][A-Za-z_0-9$./:-]*(?:\[\d+\])?$")
OUT={"X","Y","Z","ZN","Q","QN","Q_N","IQ","IQ_N","CO","COUT","SUM","CLKOUT"}
SUPPLY={"VPWR","VGND","VPB","VNB","VDD","VSS"}
CORNERS=("nom_ss_100C_1v60","max_ss_100C_1v60")
ROWS=[]
DETAILS={}

def emit(level,name,value):
    line=f"{level} | {name} | {value}"
    print(line,flush=True)
    ROWS.append(line)

def verify_file(p,name,limit=40*1024*1024):
    if p.is_symlink() or not p.is_file():
        raise RuntimeError(f"{name} missing or symlink: {p}")
    if p.stat().st_size>limit:
        raise RuntimeError(f"{name} unexpectedly large")
    return p

def checksum(p):
    h=hashlib.sha256()
    with p.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def jload(p,name):
    return json.loads(verify_file(p,name,18*1024*1024).read_text(encoding="utf-8"))

def norm(s):
    return re.sub(r"\s+","",s.strip().lstrip("\\")).strip(";")

def parse_cells(text):
    cells={}
    bynet=defaultdict(list)
    for m in CELL.finditer(text):
        inst=norm(m["name"])
        if inst in cells:
            raise RuntimeError("Duplicate gate instance "+inst)
        conns={pin:norm(net) for pin,net in PORT.findall(m["body"])}
        cells[inst]={"type":m["type"],"pins":conns}
        for pin,net in conns.items():
            if net and not re.match(r"^\d+'[bdho]",net,re.I):
                bynet[net].append({"inst":inst,"port":pin,"type":m["type"]})
    aliases=defaultdict(set)
    for m in ALIAS.finditer(text):
        a,b=norm(m[1]),norm(m[2])
        if SIMPLE.fullmatch(a) and SIMPLE.fullmatch(b):
            aliases[a].add(b)
            aliases[b].add(a)
    return cells,bynet,aliases

def selftest():
    text=r"""
module unit(input wire clk);
wire n1,n2,n3;
assign n1 = clk;
sky130_fd_sc_hd__clkdlybuf4s25_1 input1 (
    .A(n1), .X(n2)
);
sky130_fd_sc_hd__nor2_2 _297_ (.A(n2), .B(n3), .Y(_138_));
endmodule
"""
    cells,by,aliases=parse_cells(text)
    assert cells["input1"]["pins"]["A"]=="n1"
    assert cells["_297_"]["pins"]=={"A":"n2","B":"n3","Y":"_138_"}
    assert by["n2"][1]["inst"]=="_297_"
    assert "clk" in aliases["n1"]
    emit("PASS","Static gate-net parser fixture","Buffer input, NOR2 two inputs, alias and same-net attachments")

def check_evidence():
    for p,wanted,label in PINS:
        verify_file(p,label)
        got=checksum(p)
        if got!=wanted:
            raise RuntimeError(f"{label} SHA256 mismatch: {got}")
        emit("PASS",label,got[:16]+"... preserved")
    metric=jload(METRICS,"Saved final Stage3E metrics")
    if len(metric)!=305 or metric.get("design__max_slew_violation__count")!=22:
        raise RuntimeError("Unexpected final Stage 3E slew metrics")
    previous=jload(THREE_K,"Stage 3K JSON")
    if previous.get("GDS_sha256")!=PINS[0][1] or \
       previous.get("netlist_path")!=str(NETLIST) or \
       previous.get("netlist_sha256")!=checksum(verify_file(NETLIST,"Pinned mapped netlist")):
        raise RuntimeError("Stage3K GDS/netlist source integrity mismatch")
    root=previous.get("source_nets",{})
    if root.get("net27",{}).get("buffer_input")!="net1" or \
       root.get("net16",{}).get("buffer_input")!="_138_":
        raise RuntimeError("Stage3K expected A/X connections changed")
    stageh=jload(THREE_H,"Stage 3H postroute slew JSON")
    selected=stageh.get("saved_checks",{}).get("selected_snapshots",{})
    for corner,count in zip(CORNERS,(11,22)):
        if len(selected.get(corner,{}).get("violator_rows",[]))!=count:
            raise RuntimeError("Stage3H saved pin count changed: "+corner)
    emit("PASS","Pinned Stage 3K / Stage 3H evidence",
         "Two correct input nets, 11/22 corner slew checks, final mapped netlist SHA256")
    return selected

def aliases(net,graph,limit=80):
    done={net}
    pending=[net]
    while pending and len(done)<limit:
        n=pending.pop()
        for neighbor in graph.get(n,()):
            if neighbor not in done:
                done.add(neighbor); pending.append(neighbor)
    return sorted(done)

def net_drivers(net,by,graph):
    names=aliases(net,graph)
    links=[p|{"net":n} for n in names for p in by.get(n,[])]
    drivers=[p for p in links if p["port"].upper() in OUT]
    receivers=[p for p in links if p["port"].upper() not in OUT|SUPPLY]
    return names,drivers,receivers

def cell_input_trace(cellname,cells,by,graph):
    item=cells.get(cellname)
    if not item:
        raise RuntimeError(f"Expected driver cell absent: {cellname}")
    incoming={}
    for pin,net in item["pins"].items():
        if pin.upper() in OUT|SUPPLY:
            continue
        names,drivers,receivers=net_drivers(net,by,graph)
        incoming[pin]={"net":net,"aliases":names,
                       "driver_candidates":drivers[:15],
                       "connected_signal_inputs":len(receivers),
                       "direct_clk_alias":"clk" in names,
                       "direct_reset_alias":"rst_n" in names}
        summary="; ".join(f"{p['inst']}/{p['port']} {p['type']}" for p in drivers[:5])
        emit("SOURCE",cellname+"/"+pin,
             f"net={net}; output drivers={summary or 'NONE VISIBLE'}; "
             f"signal-input ports={len(receivers)}; direct clk={'clk' in names}; direct rst_n={'rst_n' in names}")
    return {"name":cellname,"cell_type":item["type"],"ports":item["pins"],"incoming":incoming}

def assess_slew(selected):
    evidence={}
    for c in CORNERS:
        rows=selected[c]["violator_rows"]
        worst=min(rows,key=lambda d:Decimal(d["slack"]))
        emit("SLEW",c,f"{len(rows)} pin checks; worst {worst['pin']} "
             f"limit={worst['limit']}ns measured={worst['slew']}ns slack={worst['slack']}ns")
        evidence[c]={"count":len(rows),"worst":worst}
    return evidence

def main():
    print("===== ASIC STAGE 3L: TT 3X2 UPSTREAM DRIVER INPUT EVIDENCE =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root WSL Ubuntu user vaish")
    if not TEMP.is_dir() or not RUN.is_dir():
        raise RuntimeError("Expected G:-backed Temp and saved 3x2 run")
    selftest()
    selected=check_evidence()
    cells,by,graph=parse_cells(NETLIST.read_text(encoding="utf-8",errors="replace"))
    signal_connected=sum(bool(x["pins"]) for x in cells.values())
    emit("PASS","Saved mapped gate netlist",
         f"{len(cells)} total instance constructs, {signal_connected} named-port instances")
    result={}
    for branch,source,src_cell,buf in (
        ("net27","net1","input1","fanout27"),
        ("net16","_138_","_297_","fanout16")
    ):
        original=cells.get(buf,{}).get("pins",{})
        src=cells.get(src_cell,{}).get("pins",{})
        if original.get("A")!=source or original.get("X")!=branch:
            raise RuntimeError("Unexpected fanout branch connection: "+branch)
        if src.get("X",src.get("Y"))!=source:
            raise RuntimeError("Upstream source output mismatch: "+src_cell)
        emit("BRANCH",branch,f"source {src_cell}/{('X' if 'X' in src else 'Y')} ({cells[src_cell]['type']}) "
             f"drives {buf}/A, output {buf}/X")
        result[branch]=cell_input_trace(src_cell,cells,by,graph)
    slew=assess_slew(selected)
    emit("REVIEW","Electrical cause and repair",
         "Source-cell input graph alone is not OpenDB load, capacitance, or actual transition fix. "
         "Do not alter RTL/constraints or ECO without electrical evidence.")
    emit("REVIEW","Physical signoff",
         "22 reported slew violations remain; KLayout DRC disabled; provider precheck/clock-IO/CDC open")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    full=TEMP/f"ASIC-Stage3L-TTSKY-3x2-Upstream-Inputs-{stamp}.json"
    brief=TEMP/f"ASIC-Stage3L-TTSKY-3x2-Summary-{stamp}.txt"
    full.write_text(json.dumps({
        "scope":"READ-ONLY signal dependency and slew evidence; not electrical timing signoff",
        "stage3k":str(THREE_K),"stage3h":str(THREE_H),
        "mapped_netlist":str(NETLIST),"mapped_netlist_sha256":checksum(NETLIST),
        "final_gds_sha256":PINS[0][1],"branch_sources":result,
        "postroute_slew":slew,
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit("PASS","Stage 3L read-only audit","No original RTL, GDS, PDK, SDC or physical output changed")
    emit("INFO","Detailed G: evidence",str(full))
    emit("INFO","Compact G: summary",str(brief))
    brief.write_text("\n".join(ROWS)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3L =====",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        print(f"FAIL | Stage 3L | {type(e).__name__}: {e}",file=sys.stderr,flush=True)
        sys.exit(1)

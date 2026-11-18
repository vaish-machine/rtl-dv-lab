#!/usr/bin/env python3
r"""ASIC Stage 3O: read-only source trace for Stage 3M remaining max-slew net.

Reads the pinned successful Stage3N report and saved Stage3M gate-level netlist.
Determines exactly what feeds fanout18/A and whether all 11 reported SS
violators are on net18. No edits, EDA flow, KLayout, or provider action.
Only new report JSON/TXT are written under G:\C-Drive-Backup-PreReset\Temp.
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

G_TEMP=Path("/mnt/g/C-Drive-Backup-PreReset/Temp")
LIB=Path("/home/vaish/DevTools/LibreLane")
RUN=LIB/"ttsky_sky130_3x2_slew_repair_trial/run-dnsp_mu6/src/runs/slewfix-3x2-20261118-105720"
OLD=LIB/"ttsky_sky130_3x2_trial/run-46NnPce8/template/src/runs/tt-3x2-20261116-123932"
NL=RUN/"final/nl/tt_um_vaish_uart.nl.v"
METRICS=RUN/"final/metrics.json"
STAGE3N=G_TEMP/"ASIC-Stage3N-TTSKY-3x2-PostRepair-Slew-20261118-123255.json"
ORIG2C=LIB/"uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
ORIG2F=LIB/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
SDC=LIB/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc"
PINNED=(
    (OLD/"final/gds/tt_um_vaish_uart.gds","4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","Original 3x2 GDS"),
    (RUN/"final/gds/tt_um_vaish_uart.gds","a095ed4615d65d2a4a557c4a14c7914ca6717bd98a8251a742128a0f3fe5a166","Stage 3M new 3x2 GDS"),
    (ORIG2C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Original Stage 2C GDS"),
    (ORIG2F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Original Stage 2F GDS"),
    (SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Original Stage 2F SDC"),
)
INSTANCE=re.compile(r"(?ms)^[ \t]*(?P<cell>sky130_[A-Za-z0-9_$]+)[ \t]+(?P<name>\\?[A-Za-z0-9_$./:-]+)[ \t]*\((?P<body>.*?)\)[ \t]*;")
PORT=re.compile(r"\.([A-Za-z_][A-Za-z_0-9$]*)\s*\(\s*([^()]*?)\s*\)",re.S)
ASSIGN=re.compile(r"(?m)^[ \t]*assign[ \t]+([^=;]+?)\s*=\s*([^;]+);")
ATOM=re.compile(r"^\\?[A-Za-z_][A-Za-z_0-9$./:-]*(?:\[\d+\])?$")
OUTPUTS={"X","Y","Z","ZN","Q","QN","Q_N","IQ","IQ_N","CO","COUT","SUM","CLKOUT"}
SUPPLIES={"VPWR","VGND","VPB","VNB","VDD","VSS"}
CORNERS=("nom_ss_100C_1v60","max_ss_100C_1v60")
LINES=[]

def emit(level,label,detail):
    line=f"{level} | {label} | {detail}"
    print(line,flush=True)
    LINES.append(line)

def checked(path,label,max_bytes=45*1024*1024):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label}: missing file or symlink: {path}")
    if path.stat().st_size>max_bytes:
        raise RuntimeError(f"{label}: unexpectedly large")
    return path

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda:f.read(1024*1024),b""):
            h.update(buf)
    return h.hexdigest()

def json_read(path,label):
    val=json.loads(checked(path,label,25*1024*1024).read_text(encoding="utf-8"))
    if not isinstance(val,dict):
        raise RuntimeError(f"{label}: expected JSON object")
    return val

def canon(text):
    return re.sub(r"\s+","",text.strip().lstrip("\\")).rstrip(";")

def parse_verilog(text):
    cells={}
    nets=defaultdict(list)
    aliases=defaultdict(set)
    for match in INSTANCE.finditer(text):
        inst=canon(match["name"])
        if inst in cells:
            raise RuntimeError(f"duplicate standard cell {inst}")
        conns={pin:canon(net) for pin,net in PORT.findall(match["body"])}
        if not conns:
            continue
        cells[inst]={"type":match["cell"],"pins":conns}
        for port,net in conns.items():
            if net:
                nets[net].append({"instance":inst,"port":port,"type":match["cell"]})
    for m in ASSIGN.finditer(text):
        a,b=canon(m[1]),canon(m[2])
        if ATOM.fullmatch(a) and ATOM.fullmatch(b):
            aliases[a].add(b)
            aliases[b].add(a)
    return cells,nets,aliases

def parser_test():
    fixture=r"""
module demo(input wire clk);
wire net18, source;
assign source = clk;
sky130_fd_sc_hd__nor2_2 _297_ (.A(net1), .B(net2), .Y(source));
sky130_fd_sc_hd__clkdlybuf4s25_1 fanout18 (.A(source), .X(net18));
sky130_fd_sc_hd__mux2_1 _336_ (.S(net18), .A0(net2), .A1(net1), .X(out1));
endmodule
"""
    cells,nets,alias=parse_verilog(fixture)
    if cells["fanout18"]["pins"]!={"A":"source","X":"net18"} or \
       cells["_336_"]["pins"]["S"]!="net18" or \
       len(nets["net18"])!=2 or "clk" not in alias["source"]:
        raise RuntimeError("gate-level cell/connectivity parser fixture failed")
    emit("PASS","Mapped gate parser fixture","Driver A/X, mux S and aliases")

def aliases_for(net,graph,limit=80):
    seen={net}
    pending=[net]
    while pending and len(seen)<limit:
        current=pending.pop()
        for other in graph.get(current,()):
            if other not in seen:
                seen.add(other)
                pending.append(other)
    return sorted(seen)

def attached(net,nets,graph):
    aliases=aliases_for(net,graph)
    endpoints=[p|{"net_alias":name} for name in aliases for p in nets.get(name,[])]
    drivers=[p for p in endpoints if p["port"].upper() in OUTPUTS]
    sinks=[p for p in endpoints if p["port"].upper() not in OUTPUTS|SUPPLIES]
    return aliases,drivers,sinks

def verify():
    for path,want,label in PINNED:
        checked(path,label)
        got=sha256(path)
        if got!=want:
            raise RuntimeError(f"{label}: SHA256 changed ({got})")
        emit("PASS",label,"SHA256 "+got[:16]+"... preserved")
    metrics=json_read(METRICS,"Stage 3M metrics")
    if len(metrics)!=307 or metrics.get("design__max_slew_violation__count")!=11:
        raise RuntimeError("Stage 3M metrics not the expected complete local trial")
    for corner in CORNERS:
        if metrics.get("design__max_slew_violation__count__corner:"+corner)!=11:
            raise RuntimeError(f"Unexpected {corner} count")
    for key in ("route__drc_errors","magic__drc_error__count",
                "klayout__drc_error__count","design__lvs_error__count",
                "timing__setup_vio__count","timing__hold_vio__count"):
        if metrics.get(key)!=0:
            raise RuntimeError(f"Missing zero metric {key}")
    comparison=json_read(STAGE3N,"Stage 3N exact G: comparison")
    if comparison.get("original_GDS_sha256")!=PINNED[0][1] or \
       comparison.get("trial_GDS_sha256")!=PINNED[1][1]:
        raise RuntimeError("Stage 3N GDS evidence mismatch")
    for corner in CORNERS:
        rows=comparison.get("postroute_slew",{}).get(corner,{}).get("trial_rows",[])
        if len(rows)!=11 or {r.get("net") for r in rows}!={"net18"}:
            raise RuntimeError(f"Stage 3N {corner}: expected 11 pin checks on net18")
    emit("PASS","Pinned final Stage 3N comparison",
         "11 nominal-SS and 11 max-SS checks on net18; trial DRC/LVS/setup/hold all zero")
    return comparison

def main():
    print("===== ASIC STAGE 3O: TT 3X2 REMAINING NET18 SOURCE TRACE =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root WSL Ubuntu user vaish")
    if not G_TEMP.is_dir() or not RUN.is_dir():
        raise RuntimeError("Expected G:-backed Temp and saved Stage 3M physical run")
    parser_test()
    prior=verify()
    netlist=checked(NL,"Stage 3M functional gate netlist")
    cells,nets,graph=parse_verilog(netlist.read_text(encoding="utf-8",errors="replace"))
    emit("PASS","Stage 3M signal-connected netlist",
         f"{len(cells)} signal-connected cell instances, SHA256 {sha256(netlist)[:16]}...")
    buf=cells.get("fanout18")
    if buf is None or buf["pins"].get("X")!="net18":
        emit("REVIEW","Expected driver","fanout18/X not connected to net18 as in OpenSTA report")
        raise RuntimeError("Cannot trace Stage3M slew branch safely")
    inp=buf["pins"].get("A")
    emit("NET","Final remaining fanout buffer",f"fanout18 ({buf['type']}): A={inp}, X=net18")
    aliases,drivers,sinks=attached("net18",nets,graph)
    emit("INFO","Remaining branch connected pins",
         f"total={len(drivers)+len(sinks)}; candidate outputs={len(drivers)}; signal receivers={len(sinks)}")
    if inp is None:
        raise RuntimeError("Missing fanout18/A input net")
    upstream_aliases,upstream_drivers,upstream_sinks=attached(inp,nets,graph)
    emit("SOURCE","fanout18/A",
         f"input net={inp}; alias names={upstream_aliases[:12]}; "
         f"candidate output drivers={len(upstream_drivers)}, receiving pins={len(upstream_sinks)}")
    chain=[]
    for record in upstream_drivers[:8]:
        cell=cells[record["instance"]]
        inports={port:net for port,net in cell["pins"].items()
                 if port.upper() not in OUTPUTS|SUPPLIES}
        entry=record|{"input_pins":inports}
        chain.append(entry)
        emit("DRIVER",f"{record['instance']}/{record['port']}",
             f"cell={cell['type']}; input nets={inports}")
        for pin,net in list(inports.items())[:6]:
            als,dr,sks=attached(net,nets,graph)
            sources=", ".join(f"{p['instance']}/{p['port']} ({p['type']})" for p in dr[:4])
            emit("PARENT",f"{record['instance']}/{pin}",
                 f"net={net}; driver={sources or 'NOT MAPPED'}; "
                 f"direct_clk={'clk' in als}; direct_rst_n={'rst_n' in als}")
    if not upstream_drivers:
        emit("REVIEW","Upstream output cell","No named output mapped; investigate input/top-level aliases")
    if inp=="_138_" and any("_297_"==e["instance"] for e in upstream_drivers):
        emit("EVIDENCE","TX decoder continuity",
             "Original _297_ signal identifier and NOR2-driver mapping preserved in new physical trial")
    else:
        emit("REVIEW","Cross-run attribution",
             "Do not assume renamed nets equal the original TX-control branch without gate source evidence")
    for corner in CORNERS:
        rows=prior["postroute_slew"][corner]["trial_rows"]
        worst=min(rows,key=lambda r:Decimal(r["slack"]))
        emit("SLEW",corner,f"11 pins; worst {worst['pin']} slew={worst['slew']}ns "
             f"limit={worst['limit']}ns, slack={worst['slack']}ns")
    emit("REVIEW","Electrical repair evidence",
         "Named-cell topology is not extracted RC/capacitance; choose buffering/resizing only in a fresh isolated trial")
    emit("REVIEW","Signoff","11 max-slew violations remain; TT provider precheck and production IO/CDC still open")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    out=G_TEMP/f"ASIC-Stage3O-TTSKY-3x2-Net18-Source-{stamp}.json"
    summary=G_TEMP/f"ASIC-Stage3O-TTSKY-3x2-Summary-{stamp}.txt"
    out.write_text(json.dumps({
        "scope":"READ-ONLY remaining post-repair SS slew net18 cell source trace; NOT electrical closure",
        "saved_GDS_sha256":PINNED[1][1],"netlist":str(NL),
        "netlist_sha256":sha256(NL),"net18_buffer":buf,
        "net18_drivers":drivers,"net18_sinks":sinks,
        "upstream_net":inp,"upstream_driver_chain":chain,
        "upstream_aliases":upstream_aliases,
        "nom_ss":prior["postroute_slew"][CORNERS[0]]["trial_rows"],
        "max_ss":prior["postroute_slew"][CORNERS[1]]["trial_rows"]
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit("PASS","Stage 3O read-only audit","No original GDS, RTL, SDC, PDK or physical run modified")
    emit("INFO","Detailed G: evidence",str(out))
    emit("INFO","Compact G: summary",str(summary))
    summary.write_text("\n".join(LINES)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3O =====",flush=True)

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"FAIL | Stage 3O | {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)

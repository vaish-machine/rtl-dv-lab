#!/usr/bin/env python3
r"""Stage 3K — read-only upstream source analysis for TT SKY130 max-slew nets.

Interrogates the saved, unmodified 3x2 Stage 3E functional gate netlist,
validated Stage 3J JSON, and the final GDS SHA256. No EDA process, routing,
KLayout, provider CI, constraint/RTL change, PDK write, or shuttle action.
Only report JSON/TXT under G:\C-Drive-Backup-PreReset\Temp are created.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys

TEMP=Path("/mnt/g/C-Drive-Backup-PreReset/Temp")
RUN=Path("/home/vaish/DevTools/LibreLane/ttsky_sky130_3x2_trial/run-46NnPce8/template/src/runs/tt-3x2-20261116-123932")
NL=RUN/"final/nl/tt_um_vaish_uart.nl.v"
GDS=RUN/"final/gds/tt_um_vaish_uart.gds"
OLD2C=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
OLD2F=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds")
SDC=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc")
STAGE3J=TEMP/"ASIC-Stage3J-TTSKY-3x2-Upstream-Clock-20261118-093553.json"
CHECKS=(
    (GDS,"4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","TT 3x2 final GDS"),
    (OLD2C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Stage 2C original GDS"),
    (OLD2F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Stage 2F original GDS"),
    (SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Stage 2F original SDC"),
)
CELL=re.compile(r"(?ms)^[ \t]*(?P<type>sky130_[A-Za-z0-9_$]+)[ \t]+(?P<name>\\?[A-Za-z0-9_$./:-]+)[ \t]*\((?P<body>.*?)\)[ \t]*;")
PORT=re.compile(r"\.([A-Za-z_][A-Za-z_0-9$]*)\s*\(\s*([^()]*?)\s*\)",re.S)
WIRE_ALIAS=re.compile(r"(?m)^[ \t]*assign[ \t]+([^=;]+?)\s*=\s*([^;]+);")
ATOM=re.compile(r"^\\?[A-Za-z_][A-Za-z_0-9$./:-]*(?:\[\d+\])?$")
OUTPUT_PORTS={"X","Y","Z","ZN","Q","QN","Q_N","IQ","IQ_N","CLKOUT","CO","COUT","SUM"}
SUPPLY_PORTS={"VPWR","VGND","VPB","VNB","VDD","VSS"}
REPORT=[]
TRACE_NODES=0
MAX_TRACE_NODES=80

def say(state,what,value):
    line=f"{state} | {what} | {value}"
    REPORT.append(line)
    print(line,flush=True)

def checked(path,label,max_size=32*1024*1024):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label}: missing file or symlink: {path}")
    if path.stat().st_size>max_size:
        raise RuntimeError(f"{label}: file unexpectedly large")
    return path

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda:stream.read(1024*1024),b""):
            h.update(data)
    return h.hexdigest()

def clean(token):
    return re.sub(r"\s+","",token.strip().lstrip("\\")).strip(";")

def extract(text):
    cells={}
    for m in CELL.finditer(text):
        name=clean(m.group("name"))
        if name in cells:
            raise RuntimeError("Duplicate mapped instance: "+name)
        cells[name]={"type":m.group("type"),
                     "ports":{pin:clean(net) for pin,net in PORT.findall(m.group("body"))}}
    connected=sum(1 for item in cells.values() if item["ports"])
    bynet=defaultdict(list)
    for inst,item in cells.items():
        for port,net in item["ports"].items():
            if net and not re.match(r"^\d+'[bdho]",net,re.I):
                bynet[net].append({"instance":inst,"port":port,"type":item["type"]})
    aliases=defaultdict(set)
    for m in WIRE_ALIAS.finditer(text):
        a,b=clean(m.group(1)),clean(m.group(2))
        if ATOM.fullmatch(a) and ATOM.fullmatch(b):
            aliases[a].add(b)
            aliases[b].add(a)
    return cells,bynet,aliases,connected

def fixture_check():
    fixture=r"""
module t(input clk, input rst_n);
  wire n1, n2, n3;
  assign n1 = clk;
  sky130_fd_sc_hd__buf_1 root_buffer (.A(n1), .X(n2));
  sky130_fd_sc_hd__clkdlybuf4s25_1 fanout27 (.A(n2), .X(n3));
  sky130_fd_sc_hd__fill_1 fill_0 ();
endmodule
"""
    cells,bynet,aliases,connected=extract(fixture)
    assert len(cells)==3 and connected==2
    assert cells["fanout27"]["ports"]=={"A":"n2","X":"n3"}
    assert "clk" in aliases["n1"]
    assert len(bynet["n2"])==2
    say("PASS","Gate-net parser self-test","Multi-line cells, signal-connected vs pinless filler, input aliases")

def verify():
    for path,expected,label in CHECKS:
        checked(path,label)
        got=sha256(path)
        if got!=expected:
            raise RuntimeError(f"{label} checksum mismatch: {got}")
        say("PASS",label,"SHA256 preserved "+got[:16]+"...")
    details=json.loads(checked(STAGE3J,"Stage 3J G: upstream trace JSON",16*1024*1024).read_text())
    if details.get("pinned_gds_sha256")!=CHECKS[0][1]:
        raise RuntimeError("Stage3J preserved GDS mismatch")
    if details.get("netlist")!=str(NL) or details.get("netlist_sha256")!=sha256(checked(NL,"Saved final gate netlist")):
        raise RuntimeError("Stage3J saved netlist identity or SHA256 mismatch")
    traces={d.get("net"):d for d in details.get("nets",[])}
    if set(traces)!={"net16","net27"}:
        raise RuntimeError("Stage3J two pinned failing net groups missing")
    for net,expected_in in (("net27","net1"),("net16","_138_")):
        entry=traces[net]
        if entry.get("driver_pins",{}).get("A")!=expected_in or \
           entry.get("driver_pins",{}).get("X")!=net:
            raise RuntimeError("Stage3J expected fanout buffer A/X wiring changed: "+net)
    say("PASS","Stage 3J evidence",
        "fanout27/A=net1, fanout16/A=_138_; outputs net27/net16 pinned to saved netlist SHA")
    return details

def alias_group(net,aliases,limit=70):
    seen={net}
    todo=[net]
    while todo and len(seen)<limit:
        cur=todo.pop()
        for other in aliases.get(cur,()):
            if other not in seen:
                seen.add(other)
                todo.append(other)
    return sorted(seen)

def output_candidates(net,bynet,aliases):
    group=alias_group(net,aliases)
    connections=[rec|{"net_alias":name} for name in group for rec in bynet.get(name,[])]
    outputs=[rec for rec in connections if rec["port"].upper() in OUTPUT_PORTS]
    inputs=[rec for rec in connections if rec["port"].upper() not in OUTPUT_PORTS]
    return group,connections,outputs,inputs

def backtrack(net,cells,bynet,aliases,depth=0,visited=None):
    global TRACE_NODES
    if visited is None: visited=set()
    TRACE_NODES+=1
    if TRACE_NODES>MAX_TRACE_NODES:
        return {"net":net,"stop":"audit_node_budget"}
    if depth>=3 or net in visited:
        return {"net":net,"stop":"depth_or_loop"}
    visited=visited|{net}
    ag,allports,drivers,sinks=output_candidates(net,bynet,aliases)
    record={
        "net":net,"alias_names":ag,
        "drivers":drivers[:8],"total_drivers":len(drivers),
        "connected_cell_pins":len(allports),
        "input_pins":len(sinks),
        "direct_clk_alias":"clk" in ag,
        "direct_rst_n_alias":"rst_n" in ag,
        "driver_inputs":[],
    }
    for dr in drivers[:3]:
        cell=cells.get(dr["instance"])
        if cell is None: continue
        inp={p:n for p,n in cell["ports"].items()
             if p.upper() not in OUTPUT_PORTS|SUPPLY_PORTS}
        if len(inp)>8: inp=dict(list(inp.items())[:8])
        step={"driver_instance":dr["instance"],"driver_output":dr["port"],
              "type":dr["type"],"input_nets":inp}
        # Trace only a few levels; this is a dependency graph, NOT a clock path proof.
        if depth<2:
            step["upstream"]={p:backtrack(n,cells,bynet,aliases,depth+1,visited)
                              for p,n in list(inp.items())[:4]
                              if not re.match(r"^\d+'[bdho]",n,re.I)}
        record["driver_inputs"].append(step)
    return record

def main():
    print("===== ASIC STAGE 3K: TT 3X2 TWO SLEW BRANCH UPSTREAM SOURCES =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root WSL Ubuntu user vaish")
    if not TEMP.is_dir() or not RUN.is_dir():
        raise RuntimeError("Expected G:-backed Temp and preserved Stage3E run")
    fixture_check()
    prior=verify()
    content=NL.read_text(encoding="utf-8",errors="replace")
    cells,bynet,aliases,connected=extract(content)
    say("PASS","Saved functional mapped netlist",
        f"{len(cells)} total instances; {connected} signal-connected instances; "
        f"{len(cells)-connected} no named ports (physical-only likely)")
    if len(cells)<300 or len(bynet)<100:
        raise RuntimeError("Unexpectedly incomplete saved gate netlist parsing")
    evidence={}
    for branch,source in (("net27","net1"),("net16","_138_")):
        buf=cells.get("fanout"+branch[3:])
        if not buf or buf["ports"].get("A")!=source or buf["ports"].get("X")!=branch:
            raise RuntimeError("Saved buffer A/X mapping differs: "+branch)
        group,allports,drivers,inputs=output_candidates(source,bynet,aliases)
        say("ROOT",branch,
            f"buffer input net={source}; aliased names={group[:8]}; "
            f"candidate cell outputs={len(drivers)}; connected pin total={len(allports)}")
        for dr in drivers[:8]:
            say("CANDIDATE",branch+" upstream cell",
                f"{dr['instance']}/{dr['port']} ({dr['type']}) on {dr['net_alias']}")
        if "clk" in group:
            say("EVIDENCE",branch,"Direct saved assign alias to top-level clk")
        elif "rst_n" in group:
            say("EVIDENCE",branch,"Direct saved assign alias to top-level rst_n")
        elif not drivers:
            say("REVIEW",branch,
                "No standard-cell output on buffer input in saved netlist; inspect top-level port assignments or ODB")
        else:
            say("REVIEW",branch,
                "Mapped upstream output candidates found, but combinational ancestry is NOT proof of clock root")
        evidence[branch]={
            "buffer_input":source,"aliases":group,
            "direct_output_candidates":drivers[:15],
            "connected_ports":allports[:50],
            "ancestry":backtrack(source,cells,bynet,aliases),
        }
    say("REVIEW","Electrical diagnosis",
        "Gate-level graph is not extracted RC/fanout load. Need OpenSTA/OpenDB electrical evidence before repairing.")
    say("REVIEW","Signoff",
        "22 SS max slew violations remain, KLayout DRC disabled, official provider precheck and clock/IO/CDC open")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    detailed=TEMP/f"ASIC-Stage3K-TTSKY-3x2-Upstream-Source-{stamp}.json"
    summary=TEMP/f"ASIC-Stage3K-TTSKY-3x2-Summary-{stamp}.txt"
    detailed.write_text(json.dumps({
        "scope":"Read-only saved mapped cell graph; no electrical driver timing or provider precheck",
        "stage3j_source":str(STAGE3J),
        "netlist_path":str(NL),"netlist_sha256":sha256(NL),
        "total_inst":len(cells),"signal_connected_inst":connected,
        "source_nets":evidence,"GDS_sha256":CHECKS[0][1]
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    say("PASS","Stage 3K read-only audit","All original RTL/GDS/SDC/PDK and physical run outputs preserved")
    say("INFO","Detailed G: JSON",str(detailed))
    say("INFO","Compact G: summary",str(summary))
    summary.write_text("\n".join(REPORT)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3K =====",flush=True)

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"FAIL | Stage 3K | {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)

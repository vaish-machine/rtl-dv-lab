#!/usr/bin/env python3
r"""ASIC Stage 3J: read-only upstream clock-buffer and fanout diagnosis.

Read the existing Stage3I report and actual final SKY130 gate-level netlist.
Trace fanout16/fanout27 X outputs and their A inputs through saved cell
connections and simple Verilog wire aliases, looking for a verifiable clock
root. Save evidence only on G: Temp. Do NOT rerun EDA, alter design/GDS/PDK,
change clock/IO constraints, run provider precheck or submit a shuttle.
"""
from __future__ import annotations
from collections import defaultdict, deque
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
METRICS=RUN/"final/metrics.json"
STAGE3I=TEMP/"ASIC-Stage3I-TTSKY-3x2-Net-Driver-20261116-171214.json"
TWO_C=Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
TWO_F=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds")
SDC=Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc")
PINNED=(
    (GDS,"4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","Original TT 3x2 GDS"),
    (TWO_C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Stage 2C GDS"),
    (TWO_F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Stage 2F GDS"),
    (SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Stage 2F SDC"),
)
INSTANCE=re.compile(r"(?ms)^[ \t]*(?P<type>sky130_[A-Za-z0-9_$]+)[ \t]+(?P<name>\\?[A-Za-z0-9_$./:-]+)[ \t]*\((?P<ports>.*?)\)[ \t]*;")
PORT=re.compile(r"\.([A-Za-z_][A-Za-z_0-9$]*)\s*\(\s*([^()]*?)\s*\)",re.S)
ASSIGN=re.compile(r"(?m)^[ \t]*assign[ \t]+([^=;]+?)\s*=\s*([^;]+);")
SIMPLE=re.compile(r"^\\?[A-Za-z_][A-Za-z_0-9$./:-]*(?:\[[0-9]+\])?$")
OUTPUTS={"X","Y","Z","ZN","Q","Q_N","QN","IQ","IQ_N","CLKOUT","CO","COUT","SUM"}
LINE=[]
DETAILS={}
def emit(level,label,message):
    s=f"{level} | {label} | {message}"
    LINE.append(s)
    print(s,flush=True)

def checked(path,label):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label}: missing or symlink: {path}")
    if path.stat().st_size>30*1024*1024:
        raise RuntimeError(f"{label}: file unexpectedly large")
    return path

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def normalize(token):
    return re.sub(r"\s+","",token.strip().lstrip("\\")).strip(";")

def parse_netlist(contents):
    cells={}
    by_net=defaultdict(list)
    for m in INSTANCE.finditer(contents):
        name=normalize(m["name"])
        pins={key:normalize(value) for key,value in PORT.findall(m["ports"])}
        if name in cells:
            raise RuntimeError(f"Duplicate mapped cell instance: {name}")
        cells[name]={"type":m["type"],"pins":pins}
        for pin,net in pins.items():
            if net and not re.match(r"^[0-9]+'[bdho]",net,re.I):
                by_net[net].append({"instance":name,"pin":pin,"cell":m["type"]})
    aliases=defaultdict(set)
    for m in ASSIGN.finditer(contents):
        lhs,rhs=normalize(m[1]),normalize(m[2])
        if SIMPLE.fullmatch(lhs) and SIMPLE.fullmatch(rhs):
            aliases[lhs].add(rhs)
            aliases[rhs].add(lhs)
    return cells,by_net,aliases

def selftest():
    t=r"""
module trial(input wire clk);
wire n1, n2;
assign n1 = clk;
sky130_fd_sc_hd__clkdlybuf4s25_1 fanout16 (.A(n1), .X(n2));
sky130_fd_sc_hd__mux2_1 _298_ (.S(n2), .A0(n1), .A1(clk), .X(n3));
endmodule
"""
    cells,links,alias=parse_netlist(t)
    assert cells["fanout16"]["pins"]=={"A":"n1","X":"n2"}
    assert "clk" in alias["n1"]
    assert len(links["n2"])==2
    emit("PASS","Gate netlist parser self-test","Clock aliases, buffer A/X and sink pins")

def check_inputs():
    for p,sha,label in PINNED:
        checked(p,label)
        if digest(p)!=sha:
            raise RuntimeError(label+" SHA256 no longer matches")
        emit("PASS",label,sha[:16]+"... preserved")
    metric=json.loads(checked(METRICS,"Stage 3E metrics").read_text())
    if metric.get("design__max_slew_violation__count")!=22:
        raise RuntimeError("Expected 22 saved Stage3E max-slew violations")
    report=json.loads(checked(STAGE3I,"Saved Stage3I G: evidence").read_text())
    if report.get("gds_sha256")!=PINNED[0][1] or \
       report.get("chosen_netlist")!=str(NL) or \
       report.get("chosen_netlist_sha256")!=digest(checked(NL,"Final functional gate netlist")):
        raise RuntimeError("Stage 3I evidence and saved functional netlist provenance mismatch")
    connections=report.get("mapped",{}).get("connections",[])
    maps={r["net"]:r for r in connections}
    if set(maps)!={"net16","net27"} or \
       any(len(maps[k]["violator_pins"])!=11 for k in maps):
        raise RuntimeError("Stage 3I expected 2 x 11 violating pin groups not found")
    emit("PASS","Pinned Stage 3I evidence",
         "22 named violations grouped as net16=11 and net27=11")
    return report,maps

def alias_cluster(root,aliases,limit=50):
    reached={root}
    queue=deque([root])
    while queue and len(reached)<=limit:
        current=queue.popleft()
        for nxt in aliases.get(current,()):
            if nxt not in reached:
                reached.add(nxt)
                queue.append(nxt)
    return reached

def candidates_for(net,by_net,aliases):
    related=alias_cluster(net,aliases)
    links=[p|{"net":n} for n in sorted(related) for p in by_net.get(n,[])]
    outputs=[p for p in links if p["pin"].upper() in OUTPUTS]
    return sorted(related),links,outputs

def trace_upstream(net,cells,by_net,aliases,depth=0,visited=None):
    if visited is None:
        visited=set()
    if depth>=8 or net in visited:
        return {"net":net,"termination":"cycle_or_depth_limit"}
    visited.add(net)
    aliased,links,outputs=candidates_for(net,by_net,aliases)
    node={"net":net,"aliases":aliased,"attached_cell_pins":len(links),
          "output_candidates":outputs[:15]}
    if "clk" in aliased:
        node["clock_source"]="Top-level signal clk appears in alias group"
    if not outputs:
        node["termination"]="No named standard-cell output detected in saved netlist"
        return node
    steps=[]
    for driver in outputs[:5]:
        cell=cells.get(driver["instance"])
        if not cell:
            continue
        # Static only: no logical arcs, delays, caps or physical clock proof.
        input_pins={k:v for k,v in cell["pins"].items()
                    if k.upper() in ("A","A1","CLK","CK","C","CLKIN","I","IN")}
        driver_info={"instance":driver["instance"],"output":driver["pin"],
                     "type":driver["cell"],"input_candidates":input_pins}
        if ("clkdlybuf" in driver["cell"] or "__buf" in driver["cell"]) \
           and input_pins.get("A"):
            driver_info["upstream"]=trace_upstream(input_pins["A"],cells,by_net,aliases,depth+1,set(visited))
        steps.append(driver_info)
    node["candidate_driver_chains"]=steps
    return node

def main():
    print("===== ASIC STAGE 3J: TT 3X2 UPSTREAM BUFFER AND CLOCK TRACE =====",flush=True)
    if os.geteuid()==0 or getpass.getuser()!="vaish":
        raise RuntimeError("Expected non-root Ubuntu user vaish")
    if not TEMP.is_dir() or not RUN.is_dir():
        raise RuntimeError("Expected G: Temp and saved Stage 3E physical run")
    selftest()
    saved,groups=check_inputs()
    cells,by_net,aliases=parse_netlist(NL.read_text(encoding="utf-8",errors="replace"))
    emit("PASS","Final functional gate netlist",
         f"{len(cells)} mapped cell instances; {len(by_net)} named connected nets")
    records=[]
    for net in ("net27","net16"):
        data=groups[net]
        expected=f"fanout{net[3:]}"
        drv=cells.get(expected)
        if not drv:
            emit("REVIEW",net,expected+" not found in functional netlist")
            records.append({"net":net,"reason":"candidate driver not present"})
            continue
        inputs=drv["pins"]
        output_net=inputs.get("X")
        if output_net!=net:
            emit("REVIEW",net,f"Driver output X maps to {output_net}, not expected {net}")
        chain=trace_upstream(inputs.get("A","<missing>"),cells,by_net,aliases)
        related,connected,outputs=candidates_for(net,by_net,aliases)
        sinks=[x for x in connected if x["pin"].upper() not in OUTPUTS]
        source_matches=[x for x in outputs if x["instance"]==expected and x["pin"]=="X"]
        emit("NET",net,
             f"candidate driver={expected} ({drv['type']}); "
             f"A={inputs.get('A','NOT MAPPED')}; X={output_net}; "
             f"connected cell inputs={len(sinks)}; output candidates={len(outputs)}")
        emit("INFO",net+" reported violations",
             f"{len(data['violator_pins'])} pins; driver X in violation list="
             f"{expected+'/X' in data['violator_pins']}; "
             f"driver X connected in netlist={bool(source_matches)}")
        if "clkdlybuf" in drv["type"]:
            emit("EVIDENCE",net,"Source cell belongs to SKY130 clock-delay-buffer family")
        else:
            emit("REVIEW",net,"Not a SKY130 clock delay buffer; examine actual type")
        root_clocks=[]
        def collect(n):
            if not isinstance(n,dict):
                return
            if n.get("clock_source"):
                root_clocks.append(n.get("net"))
            for e in n.get("candidate_driver_chains",[]):
                collect(e.get("upstream"))
        collect(chain)
        if root_clocks:
            emit("EVIDENCE",net,"Static upstream alias/clock path reaches top-level clk via "+", ".join(root_clocks))
        else:
            emit("REVIEW",net,"No verified path to top-level clk in static alias/driver walk; do NOT claim source is clock")
        records.append({"net":net,"buffer":expected,"buffer_type":drv["type"],
                        "driver_pins":inputs,"connected_cell_inputs":sinks,
                        "net_outputs":outputs,"net_aliases":related,
                        "upstream_trace":chain,"clock_alias_roots":root_clocks})
    emit("REVIEW","Electrical root cause",
         "Clock buffer family and net connectivity alone cannot prove capacitance, slew repair method or actual OpenDB clock-tree timing")
    emit("REVIEW","Signoff",
         "22 max-slew violations and disabled KLayout DRC remain; no provider precheck/IO/CDC signoff")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    details=TEMP/f"ASIC-Stage3J-TTSKY-3x2-Upstream-Clock-{stamp}.json"
    summary=TEMP/f"ASIC-Stage3J-TTSKY-3x2-Summary-{stamp}.txt"
    details.write_text(json.dumps({
        "scope":"READ-ONLY static functional gate netlist upstream buffer trace; NOT OpenDB/STA proof",
        "netlist":str(NL),"netlist_sha256":digest(NL),
        "source_stage3i":str(STAGE3I),"pinned_gds_sha256":PINNED[0][1],
        "nets":records,
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit("PASS","Stage 3J read-only audit","No original RTL, GDS, PDK, SDC or EDA output changed")
    emit("INFO","Detailed G: evidence",str(details))
    emit("INFO","Compact G: summary",str(summary))
    summary.write_text("\n".join(LINE)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3J =====",flush=True)

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"FAIL | Stage 3J | {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)

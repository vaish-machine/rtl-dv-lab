#!/usr/bin/env python3
r"""ASIC Stage 3Q: READ-ONLY Stage3P post-GRT slew regression analysis.

Audit the saved Stage3M best local trial against the Stage3P 40%-margin
regression using the actual final gate netlists and OpenSTA postroute
max-slew reports at three SS corners. Summarize failing sink groups by
net, candidate cell output, buffer input, and immediate upstream source
cell, with clock/reset/TX-state labels ONLY when directly supported.

The original 3x2 GDS, Stage3M GDS, new Stage3P GDS, original standalone
GDS/SDC and all RTL/PDK/physical run outputs are READ ONLY. The only
new outputs are JSON and TXT under G:\C-Drive-Backup-PreReset\Temp.
No OpenROAD, LibreLane, KLayout, route, ECO, or provider precheck.
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
BASE=Path("/home/vaish/DevTools/LibreLane")
E=BASE/"ttsky_sky130_3x2_trial/run-46NnPce8/template/src/runs/tt-3x2-20261116-123932"
M=BASE/"ttsky_sky130_3x2_slew_repair_trial/run-dnsp_mu6/src/runs/slewfix-3x2-20261118-105720"
P=BASE/"ttsky_sky130_3x2_postgrt_margin_trial/run-fjbwtksg/src/runs/postgrt40-3x2-20261118-132424"
PW=BASE/"ttsky_sky130_3x2_postgrt_margin_trial/run-fjbwtksg"
OLD2C=BASE/"uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
OLD2F=BASE/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
OLD_SDC=BASE/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc"
IMMUTABLE=(
    (E/"final/gds/tt_um_vaish_uart.gds","4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","Stage3E original TT GDS"),
    (M/"final/gds/tt_um_vaish_uart.gds","a095ed4615d65d2a4a557c4a14c7914ca6717bd98a8251a742128a0f3fe5a166","Stage3M best TT GDS"),
    (P/"final/gds/tt_um_vaish_uart.gds","0565ef206a746c4e6e4e90449a823be79d1956b45d9ba9ba2ce84fa086251533","Stage3P regressed TT GDS"),
    (OLD2C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Stage2C original GDS"),
    (OLD2F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Stage2F original GDS"),
    (OLD_SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Stage2F provisional SDC"),
)
CORNERS=("nom_ss_100C_1v60","min_ss_100C_1v60","max_ss_100C_1v60")
EXPECTED={"nom_ss_100C_1v60":(11,22),"min_ss_100C_1v60":(11,11),"max_ss_100C_1v60":(11,33)}
FLOAT=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
ROW=re.compile(r"^\s*(\S+)\s+("+FLOAT+r")\s+("+FLOAT+r")\s+("+FLOAT+r")(?:\s+\((VIOLATED|MET)\))?\s*$",re.I)
HEADER=re.compile(r"(?i)\bPin\b.*\bLimit\b.*\bSlew\b.*\bSlack\b")
INSTANCE=re.compile(r"(?ms)^[ \t]*(?P<type>sky130_[A-Za-z0-9_$]+)[ \t]+(?P<inst>\\?[A-Za-z0-9_$./:-]+)[ \t]*\((?P<body>.*?)\)[ \t]*;")
PIN=re.compile(r"\.([A-Za-z_][A-Za-z_0-9$]*)\s*\(\s*([^()]*?)\s*\)",re.S)
ASSIGN=re.compile(r"(?m)^[ \t]*assign[ \t]+([^=;]+?)\s*=\s*([^;]+);")
ATOM=re.compile(r"^\\?[A-Za-z_][A-Za-z_0-9$./:-]*(?:\[\d+\])?$")
OUT={"X","Y","Z","ZN","Q","QN","Q_N","IQ","IQ_N","CO","COUT","SUM","CLKOUT"}
SUPPLIES={"VPWR","VGND","VPB","VNB","VDD","VSS"}
DISPLAY=[]
OUTPUT={"scope":"READ ONLY local 3x2 post-GRT regression; no EDA or provider checks"}

def say(level,label,message):
    line=f"{level} | {label} | {message}"
    DISPLAY.append(line)
    print(line,flush=True)

def path_file(path,label,maximum=45*1024*1024):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label}: missing or symlink: {path}")
    if path.stat().st_size>maximum:
        raise RuntimeError(f"{label}: unusually large: {path}")
    return path

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def jread(path,label):
    value=json.loads(path_file(path,label).read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise RuntimeError(f"{label}: expected JSON object")
    return value

def canon(name):
    return re.sub(r"\s+","",name.strip().lstrip("\\")).rstrip(";")

def parse_netlist(path):
    data=path_file(path,"saved final mapped netlist").read_text(encoding="utf-8",errors="replace")
    cells={}
    bynet=defaultdict(list)
    aliases=defaultdict(set)
    for match in INSTANCE.finditer(data):
        inst=canon(match.group("inst"))
        ports={p:canon(net) for p,net in PIN.findall(match.group("body"))}
        if not ports:
            continue
        if inst in cells:
            raise RuntimeError(f"duplicate connected mapped cell {inst}")
        cell_type=match.group("type")
        cells[inst]={"type":cell_type,"ports":ports}
        for port,net in ports.items():
            if net and not re.match(r"^\d+'[bdho]",net,re.I):
                bynet[net].append({"inst":inst,"port":port,"type":cell_type})
    for m in ASSIGN.finditer(data):
        a,b=canon(m[1]),canon(m[2])
        if ATOM.fullmatch(a) and ATOM.fullmatch(b):
            aliases[a].add(b)
            aliases[b].add(a)
    return cells,bynet,aliases

def cluster(root,aliases,max_nodes=80):
    reached={root}
    work=[root]
    while work and len(reached)<max_nodes:
        cur=work.pop()
        for link in aliases.get(cur,()):
            if link not in reached:
                reached.add(link)
                work.append(link)
    return sorted(reached)

def net_summary(net,cells,bynet,aliases):
    names=cluster(net,aliases)
    pins=[p|{"net_alias":n} for n in names for p in bynet.get(n,())]
    drivers=[p for p in pins if p["port"].upper() in OUT]
    sinks=[p for p in pins if p["port"].upper() not in OUT|SUPPLIES]
    details=[]
    for dr in drivers[:8]:
        cell=cells.get(dr["inst"])
        if cell is None:
            continue
        inputs={p:n for p,n in cell["ports"].items() if p.upper() not in OUT|SUPPLIES}
        parents=[]
        for pin,parent_net in list(inputs.items())[:8]:
            pname=cluster(parent_net,aliases)
            par=[p for n in pname for p in bynet.get(n,()) if p["port"].upper() in OUT]
            parents.append({"port":pin,"net":parent_net,
                            "root_aliases":{"clk":"clk" in pname,"rst_n":"rst_n" in pname},
                            "driver_candidates":par[:6]})
        details.append({"output":dr,"cell_type":cell["type"],
                        "input_pins":inputs,"upstream_parent_pins":parents})
    return {"aliases":names,"driver_outputs":details,
            "driver_count":len(drivers),"sink_count":len(sinks),
            "sink_pins":sinks,"direct_root_aliases":{"clk":"clk" in names,"rst_n":"rst_n" in names}}

def parse_slew(text):
    lines=text.splitlines()
    rows=[]
    for i,line in enumerate(lines):
        if line.strip().lower()!="max slew":
            continue
        hdr=None
        for j in range(i+1,min(i+15,len(lines))):
            if HEADER.search(lines[j]):
                hdr=j
                break
        if hdr is None:
            continue
        for j in range(hdr+1,min(hdr+1100,len(lines))):
            st=lines[j].strip()
            if re.match(r"(?i)^max (?:fanout|capacitance|cap|slew violation count)\b",st) or re.match(r"^={8,}",st):
                break
            m=ROW.match(lines[j])
            if m is None:
                continue
            p,limit,slew,slack,status=m.groups()
            if Decimal(slack)<0 or (status or "").upper()=="VIOLATED":
                rows.append({"pin":p,"limit_ns":limit,"slew_ns":slew,"slack_ns":slack,"line":j+1})
    unique={}
    for r in rows:
        if r["pin"] not in unique or Decimal(r["slack_ns"])<Decimal(unique[r["pin"]]["slack_ns"]):
            unique[r["pin"]]=r
    return sorted(unique.values(),key=lambda x:Decimal(x["slack_ns"]))

def parser_test():
    fixture=r"""module t(input wire rst_n);
sky130_fd_sc_hd__clkdlybuf4s25_1 input1 (.A(rst_n),.X(net1));
sky130_fd_sc_hd__buf_1 fanout18 (.A(net1),.X(net18));
sky130_fd_sc_hd__mux2_1 _336_ (.S(net18),.A0(x),.A1(y),.X(z));
endmodule
"""
    cells,nets,alias=parse_netlist_fixture(fixture)
    assert len(cells)==3 and cells["fanout18"]["ports"]=={"A":"net1","X":"net18"}
    assert net_summary("net18",cells,nets,alias)["sink_count"]==1
    r=parse_slew("max slew\nPin Limit Slew Slack\n_336_/S 0.750000 0.907657 -0.157657 (VIOLATED)\nmax fanout\n")
    assert len(r)==1 and r[0]["pin"]=="_336_/S"
    say("PASS","Netlist/OpenSTA parser fixtures","Multi-line SKY130 A/X, input sinks and violated slew rows")

def parse_netlist_fixture(contents):
    # The same parsing rules as parse_netlist, for self-test without filesystem.
    cells={}
    nets=defaultdict(list)
    alias=defaultdict(set)
    for m in INSTANCE.finditer(contents):
        inst=canon(m.group("inst"))
        ports={p:canon(net) for p,net in PIN.findall(m.group("body"))}
        cells[inst]={"type":m.group("type"),"ports":ports}
        for p,net in ports.items():
            nets[net].append({"inst":inst,"port":p,"type":m.group("type")})
    return cells,nets,alias

def verify():
    for path,want,label in IMMUTABLE:
        value=sha256(path_file(path,label))
        if value!=want:
            raise RuntimeError(f"{label} SHA256 changed {value}")
        say("PASS",label,want[:16]+"... preserved")
    m=jread(M/"final/metrics.json","Stage3M final metrics")
    p=jread(P/"final/metrics.json","Stage3P final metrics")
    if len(m)!=307 or len(p)!=307:
        raise RuntimeError("Saved final metrics missing or wrong size")
    if m.get("design__max_slew_violation__count")!=11 or p.get("design__max_slew_violation__count")!=33:
        raise RuntimeError("Saved Stage3M/Stage3P slew totals unexpected")
    for c,(before,after) in EXPECTED.items():
        key="design__max_slew_violation__count__corner:"+c
        if m.get(key)!=before or p.get(key)!=after:
            raise RuntimeError(f"Saved SS counts differ for {c}: {m.get(key)}, {p.get(key)}")
    for key in ("route__drc_errors","magic__drc_error__count","klayout__drc_error__count",
                "design__lvs_error__count","timing__setup_vio__count","timing__hold_vio__count"):
        if m.get(key)!=0 or p.get(key)!=0:
            raise RuntimeError(f"Local DRC/LVS/timing counter is not clean {key}")
    comparison=jread(PW/"comparison.json","Stage3P comparison")
    prov=jread(PW/"provenance.json","Stage3P provenance")
    if comparison.get("stage3p_GDS_sha256")!=IMMUTABLE[2][1] or \
       comparison.get("stage3m_GDS_sha256")!=IMMUTABLE[1][1] or \
       prov.get("old_Stage3M_GDS_sha256")!=IMMUTABLE[1][1]:
        raise RuntimeError("Stage3P provenance SHA256 does not match expected GDS")
    cfg=jread(PW/"src/config_3p.json","Stage3P config")
    if cfg.get("GRT_DESIGN_REPAIR_MAX_SLEW_PCT")!=40 or \
       cfg.get("DESIGN_REPAIR_MAX_SLEW_PCT")!=30 or \
       cfg.get("RUN_POST_GRT_DESIGN_REPAIR") not in (True,1) or \
       cfg.get("RUN_KLAYOUT_DRC") not in (True,1) or \
       str(cfg.get("CLOCK_PERIOD")) not in ("100","100.0"):
        raise RuntimeError("Stage3P trial physical/repair configuration differs")
    say("PASS","Pinned Stage3P experiment","Only post-GRT margin changed; 100ns clock/30pct early margin/KLayout preserved")
    for key in ("design__max_slew_violation__count","route__drc_errors","magic__drc_error__count",
                "klayout__drc_error__count","design__lvs_error__count",
                "timing__setup_vio__count","timing__hold_vio__count",
                "design__instance__area__stdcell"):
        say("METRIC",key,f"Stage3M={m.get(key)}; Stage3P={p.get(key)}")
    OUTPUT["metric_comparison"]={k:{"Stage3M":m.get(k),"Stage3P":p.get(k)}
                                 for k in set(m)|set(p) if "slew" in k or k in (
                                     "route__drc_errors","klayout__drc_error__count",
                                     "magic__drc_error__count","design__lvs_error__count")}
    return m,p

def report_path(run,corner):
    matches=[]
    for path in run.rglob("checks.rpt"):
        if not path.is_file() or path.is_symlink() or path.stat().st_size>8*1024*1024:
            continue
        rel=path.relative_to(run)
        if len(rel.parts)>2 and corner in rel.parts and "stapostpnr" in rel.parts[0].lower():
            m=re.match(r"(\d+)-",rel.parts[0])
            matches.append((int(m.group(1)) if m else -1,path))
    return max(matches,key=lambda x:x[0])[1] if matches else None

def trace():
    mapped={}
    for name,run in (("Stage3M",M),("Stage3P",P)):
        nl=run/"final/nl/tt_um_vaish_uart.nl.v"
        cells,bynet,aliases=parse_netlist(nl)
        say("PASS",name+" final mapped netlist",f"{len(cells)} signal-connected SKY130 cells")
        mapped[name]={"cells":cells,"nets":bynet,"aliases":aliases,"netlist":str(nl),
                      "netlist_sha256":sha256(nl)}
    grouped_evidence={}
    for corner in CORNERS:
        specific={}
        for name,run in (("Stage3M",M),("Stage3P",P)):
            selected=report_path(run,corner)
            if selected is None:
                say("REVIEW",f"{name} saved postroute {corner}","No checks.rpt found, no per-pin claim")
                specific[name]={"report":None,"rows":[],"net_groups":{}}
                continue
            rows=parse_slew(selected.read_text(encoding="utf-8",errors="replace"))
            exp=EXPECTED[corner][0 if name=="Stage3M" else 1]
            say("PASS" if len(rows)==exp else "REVIEW",f"{name} {corner} OpenSTA pins",
                f"{len(rows)} parsed vs {exp} saved violations")
            cells=mapped[name]["cells"]
            grp=defaultdict(list)
            for r in rows:
                if "/" not in r["pin"]:
                    grp["UNRESOLVED"].append(r|{"net":None,"reason":"no cell/pin separator"})
                    continue
                inst,port=r["pin"].rsplit("/",1)
                item=cells.get(canon(inst))
                net=item["ports"].get(port) if item else None
                grp[net or "UNRESOLVED"].append(r|{"net":net,
                    "cell_type":item["type"] if item else None})
            groups={}
            for net,pins in sorted(grp.items(),key=lambda item:-len(item[1])):
                worst=min(pins,key=lambda x:Decimal(x["slack_ns"]))
                say("NET",f"{name} {corner}",
                    f"{net}: violations={len(pins)}, worst={worst['pin']}, "
                    f"slew={worst['slew_ns']}ns, slack={worst['slack_ns']}ns")
                for r in pins[:4]:
                    say("PIN",f"{name} {net}",f"{r['pin']}, slew={r['slew_ns']}ns, slack={r['slack_ns']}ns")
                info=None
                if net!="UNRESOLVED":
                    info=net_summary(net,cells,mapped[name]["nets"],mapped[name]["aliases"])
                    for dr in info["driver_outputs"][:3]:
                        say("DRIVER",f"{name} {net}",
                            f"{dr['output']['inst']}/{dr['output']['port']} ({dr['cell_type']}), "
                            f"input nets={dr['input_pins']}")
                        for parent in dr["upstream_parent_pins"][:4]:
                            pd=parent["driver_candidates"]
                            sources=", ".join(f"{d['inst']}/{d['port']} ({d['type']})" for d in pd[:4])
                            say("SOURCE",f"{name} {net}",
                                f"driver input {parent['port']}={parent['net']}; source={sources or 'none named'}; "
                                f"direct rst_n={parent['root_aliases']['rst_n']}")
                groups[net]={"count":len(pins),"worst":worst,"pins":pins,"candidate_net_source":info}
            specific[name]={"report":str(selected),"rows":rows,"net_groups":groups}
        grouped_evidence[corner]=specific
    OUTPUT["analysis"]=grouped_evidence
    # Interpret only evidence; do not infer logical net identity from names across independent flows.
    say("REVIEW","Root-cause status",
        "Pin/cell names are run-local; map each actual source. Static connected netlist is NOT extracted-RC timing proof.")
    say("REVIEW","Physical signoff",
        "Stage3M has 11 max-slew checks, Stage3P 33; provider GDS/precheck and host clock/IO/CDC OPEN")

def main():
    print("===== ASIC STAGE 3Q: TT 3X2 POST-GRT REGRESSION ROOT NET GROUPS =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root Ubuntu user vaish")
    if not TEMP.is_dir() or not M.is_dir() or not P.is_dir():
        raise RuntimeError("Missing G: Temp or saved Stage3M/Stage3P trials")
    parser_test()
    verify()
    trace()
    # Revalidate physical GDS hashes after report and netlist inspections.
    for path,want,label in IMMUTABLE:
        if sha256(path_file(path,label))!=want:
            raise RuntimeError("Unexpected original GDS/SDC mutation after audit")
    say("PASS","Stage3Q read-only baseline protection",
        "Stage3E/3M/3P/2C/2F GDS and provisional SDC SHA256s unchanged")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    path=TEMP/f"ASIC-Stage3Q-TTSKY-3x2-Regression-Net-Groups-{stamp}.json"
    summary=TEMP/f"ASIC-Stage3Q-TTSKY-3x2-Summary-{stamp}.txt"
    OUTPUT.update({"Stage3M_GDS":IMMUTABLE[1][1],"Stage3P_GDS":IMMUTABLE[2][1],
                   "read_only":True})
    path.write_text(json.dumps(OUTPUT,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    say("INFO","Detailed G: evidence",str(path))
    say("INFO","Compact G: summary",str(summary))
    summary.write_text("\n".join(DISPLAY)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3Q =====",flush=True)

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL | Stage3Q | {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)

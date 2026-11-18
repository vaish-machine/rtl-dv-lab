#!/usr/bin/env python3
r"""ASIC Stage 3P: isolated post-GRT slew repair margin experiment, SKY130 TT 3x2.

Only NEW copy of Stage3M's known-complete RTL/DEF/physical config is changed:
GRT_DESIGN_REPAIR_MAX_SLEW_PCT = 40 (documented default 10). All other
config entries remain byte-equivalent by value (including 100ns clock,
DESIGN_REPAIR_MAX_SLEW_PCT=30, post-GRT repair and KLayout DRC enabled).
No SDC limit relaxation, no RTL rewrite. New PnR is in a unique native
G:-backed WSL ext4 folder. Existing Stage3E/3M/2C/2F GDS/SDC untouched.
This is LOCAL exploratory PnR, not provider TT GDS Action or precheck.
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
import shutil
import subprocess
import sys
import tempfile

G=Path("/mnt/g/C-Drive-Backup-PreReset")
TEMP=G/"Temp"
TOOLS=Path("/home/vaish/DevTools/LibreLane")
BASE=TOOLS/"ttsky_sky130_3x2_postgrt_margin_trial"
OLD=TOOLS/"ttsky_sky130_3x2_slew_repair_trial/run-dnsp_mu6"
OLD_RUN=OLD/"src/runs/slewfix-3x2-20261118-105720"
SOURCE3E=TOOLS/"ttsky_sky130_3x2_trial/run-46NnPce8/template"
APP=TOOLS/"3.0.17/librelane-devshell-x86_64.AppImage"
PDK=TOOLS/"pdks"
TT_DEF="tt/tech/sky130A/def/tt_block_3x2_pg.def"
FILES=("tt_um_vaish_uart.v","uart_core.sv","uart_tx.sv","uart_rx.sv")
OLD2C=TOOLS/"uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
OLD2F=TOOLS/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
SDC=TOOLS/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc"
IMMUTABLE=(
    (SOURCE3E/"src/runs/tt-3x2-20261116-123932/final/gds/tt_um_vaish_uart.gds",
     "4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599","Stage3E TT baseline GDS"),
    (OLD_RUN/"final/gds/tt_um_vaish_uart.gds",
     "a095ed4615d65d2a4a557c4a14c7914ca6717bd98a8251a742128a0f3fe5a166","Stage3M repaired TT baseline GDS"),
    (OLD2C,"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3","Stage2C original GDS"),
    (OLD2F,"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af","Stage2F original GDS"),
    (SDC,"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4","Stage2F original SDC"),
    (APP,"c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c","LibreLane pinned AppImage"),
)
CORNERS=("nom_tt_025C_1v80","nom_ss_100C_1v60","nom_ff_n40C_1v95",
         "min_tt_025C_1v80","min_ss_100C_1v60","min_ff_n40C_1v95",
         "max_tt_025C_1v80","max_ss_100C_1v60","max_ff_n40C_1v95")
COMPARE=(
    "design__max_slew_violation__count",
    "design__max_slew_violation__count__corner:nom_ss_100C_1v60",
    "design__max_slew_violation__count__corner:max_ss_100C_1v60",
    "route__drc_errors","magic__drc_error__count","klayout__drc_error__count",
    "design__lvs_error__count","timing__setup_vio__count","timing__hold_vio__count",
    "design__instance__area__stdcell","design__instance__utilization__stdcell",
)
FLOAT=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
LINE_RE=re.compile(r"^\s*(\S+)\s+("+FLOAT+r")\s+("+FLOAT+r")\s+("+FLOAT+r")(?:\s+\((VIOLATED|MET)\))?\s*$",re.I)
HEADER=re.compile(r"(?i)\bPin\b.*\bLimit\b.*\bSlew\b.*\bSlack\b")
LOG=[]
WORK=None

def show(kind,name,value):
    line=f"{kind} | {name} | {value}"
    print(line,flush=True)
    LOG.append(line)

def check(path,label):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label} missing or symlink: {path}")
    return path

def hash_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def json_read(path,label):
    return json.loads(check(path,label).read_text(encoding="utf-8"))

def validate_hashes():
    for path,want,label in IMMUTABLE:
        got=hash_file(check(path,label))
        if got!=want:
            raise RuntimeError(f"{label} hash changed: {got}")
    show("PASS","Preserved baselines","Stage3E/3M/2C/2F GDS, SDC and AppImage pinned SHA256 intact")

def summary():
    if TEMP.is_dir():
        path=TEMP/("ASIC-Stage3P-TTSKY-3x2-PostGRT-Margin-"+datetime.now().strftime("%Y%m%d-%H%M%S")+".txt")
        path.write_text("\n".join(LOG)+"\n",encoding="utf-8")
        print(f"INFO | G: summary | {path}",flush=True)

def failure(msg):
    show("FAIL","Stage3P",msg)
    if WORK is not None:
        log=WORK/"physical-flow.log"
        if log.is_file():
            show("INFO","Full preserved physical-flow log",str(log))
            try:
                from collections import deque
                with log.open(encoding="utf-8",errors="replace") as f:
                    tail=list(deque(f,maxlen=90))
                useful=[l.strip()[:320] for l in tail if
                        any(x in l.lower() for x in ("error","failed","traceback","unknown","validation"))]
                for item in useful[-8:]:
                    show("DIAG","LibreLane",item)
                for item in tail[-5:]:
                    show("TAIL","LibreLane",item.strip()[:320])
            except Exception:
                pass
        show("INFO","Isolated trial retained",str(WORK))
    summary()
    sys.exit(1)

def parse_report(text):
    rows=[]
    lines=text.splitlines()
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
        for j in range(hdr+1,min(hdr+1000,len(lines))):
            s=lines[j].strip()
            if re.match(r"(?i)^max (?:fanout|capacitance|cap|slew violation count)\b",s) or re.match(r"^={8,}",s):
                break
            m=LINE_RE.match(lines[j])
            if not m:
                continue
            pin,limit,slew,slack,status=m.groups()
            if Decimal(slack)<0 or (status or "").upper()=="VIOLATED":
                rows.append({"pin":pin,"limit_ns":limit,"slew_ns":slew,"slack_ns":slack})
    unique={}
    for x in rows:
        if x["pin"] not in unique or Decimal(x["slack_ns"])<Decimal(unique[x["pin"]]["slack_ns"]):
            unique[x["pin"]]=x
    return sorted(unique.values(),key=lambda x:Decimal(x["slack_ns"]))

def test_parser():
    sample="""max slew
Pin Limit Slew Slack
_336_/S 0.750000 0.871323 -0.121323 (VIOLATED)
max fanout
"""
    r=parse_report(sample)
    if len(r)!=1 or r[0]["pin"]!="_336_/S":
        raise RuntimeError("Saved OpenSTA row parser failed self-test")
    show("PASS","Saved OpenSTA report parser","Slew-limit/transition/negative-slack fixture")

def preflight():
    global WORK
    print("===== ASIC STAGE 3P: ISOLATED TTSKY 3X2 POST-GRT SLEW MARGIN TRIAL =====",flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0 or not TEMP.is_dir() or not TOOLS.is_dir():
        raise RuntimeError("Expected WSL vaish and G:-backed Temp/native tools")
    free=shutil.disk_usage(G).free
    if free < 20*1024**3:
        raise RuntimeError(f"Insufficient G: free space {free/1024**3:.1f} GiB")
    show("PASS","G: storage",f"{free/1024**3:.1f} GiB free")
    validate_hashes()
    test_parser()
    prov=json_read(SOURCE3E/"LOCAL_TRIAL_PROVENANCE.json","Stage3E source provenance")
    if prov.get("tile")!="3x2":
        raise RuntimeError("Original Stage3E 3x2 manifest mismatch")
    for name in FILES:
        expected=prov.get("source_sha256",{}).get(name)
        if hash_file(check(OLD/"src"/name,"Stage3M source "+name))!=expected or \
           hash_file(check(SOURCE3E/"src"/name,"Stage3E source "+name))!=expected:
            raise RuntimeError("UART RTL source differs from original: "+name)
    show("PASS","Four UART RTL files","Identical to original Stage3E source hashes")
    oldcfg=json_read(OLD/"src/config_3m.json","Stage3M trial configuration")
    fixed={
        "CLOCK_PERIOD":100,
        "DESIGN_NAME":"tt_um_vaish_uart",
        "FP_DEF_TEMPLATE":"dir::../tt/tech/sky130A/def/tt_block_3x2_pg.def",
        "DIE_AREA":"0 0 508.76 225.76",
        "DEFAULT_CORNER":"max_ss_100C_1v60",
        "DESIGN_REPAIR_MAX_SLEW_PCT":30,
        "RUN_POST_GRT_DESIGN_REPAIR":True,
        "RUN_KLAYOUT_DRC":1,
    }
    for key,want in fixed.items():
        if oldcfg.get(key)!=want:
            raise RuntimeError(f"Stage3M {key} expected {want}, observed {oldcfg.get(key)}")
    if oldcfg.get("GRT_DESIGN_REPAIR_MAX_SLEW_PCT",10)!=10:
        raise RuntimeError("Stage3M already changed post-GRT slew margin; trial would not isolate one variable")
    origdef=check(SOURCE3E/TT_DEF,"Official TT 3x2 DEF")
    lastdef=check(OLD/TT_DEF,"Stage3M TT 3x2 DEF")
    if hash_file(lastdef)!=hash_file(origdef):
        raise RuntimeError("Stage3M TT DEF differs from original")
    if "DIEAREA ( 0 0 ) ( 508760 225760 ) ;" not in lastdef.read_text(encoding="utf-8"):
        raise RuntimeError("Provider 3x2 tile geometry unexpected")
    prior=json_read(OLD_RUN/"final/metrics.json","Stage3M final metrics")
    if len(prior)!=307 or prior.get("design__max_slew_violation__count")!=11 or \
       any(prior.get(k)!=0 for k in ("route__drc_errors","magic__drc_error__count",
                                     "klayout__drc_error__count","design__lvs_error__count",
                                     "timing__setup_vio__count","timing__hold_vio__count")):
        raise RuntimeError("Saved Stage3M physical metrics differ from established reference")
    BASE.mkdir(parents=True,exist_ok=True)
    WORK=Path(tempfile.mkdtemp(prefix="run-",dir=BASE))
    (WORK/"src").mkdir()
    outdef=WORK/TT_DEF
    outdef.parent.mkdir(parents=True)
    shutil.copy2(lastdef,outdef)
    for name in FILES:
        shutil.copy2(OLD/"src"/name,WORK/"src"/name)
        if hash_file(WORK/"src"/name)!=hash_file(OLD/"src"/name):
            raise RuntimeError(f"Copied RTL changed: {name}")
    if hash_file(outdef)!=hash_file(lastdef):
        raise RuntimeError("Copied TT DEF changed")
    new=dict(oldcfg)
    new["GRT_DESIGN_REPAIR_MAX_SLEW_PCT"]=40
    differing={k for k in set(new)|set(oldcfg) if new.get(k)!=oldcfg.get(k)}
    if differing!={"GRT_DESIGN_REPAIR_MAX_SLEW_PCT"}:
        raise RuntimeError("Stage3P trial unexpectedly changes other config values")
    cfg=WORK/"src/config_3p.json"
    cfg.write_text(json.dumps(new,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (WORK/"provenance.json").write_text(json.dumps({
        "scope":"LOCAL TT 3x2 post-GRT slew margin experiment; NOT provider TT GDS Action",
        "old_Stage3M_GDS_sha256":IMMUTABLE[1][1],
        "old_Stage3E_GDS_sha256":IMMUTABLE[0][1],
        "config_change_only":{"GRT_DESIGN_REPAIR_MAX_SLEW_PCT":{"from_default":10,"to":40}},
        "clock_ns":100,"no_RTL_edit":True,"no_slew_limit_relaxation":True,
        "config_sha256":hash_file(cfg),
        "rtl_sha256":{name:hash_file(WORK/"src"/name) for name in FILES},
        "provider_DEF_sha256":hash_file(outdef),
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    show("PASS","New isolated G:-backed physical workspace",str(WORK))
    show("PASS","One-variable controlled experiment",
         "Post-GRT slew margin default 10% -> 40%; early repair stays 30%")
    show("PASS","Preserved timing and physical configuration",
         "100ns clock, original slew limit, same TT 3x2 DEF, KLayout DRC enabled")
    return cfg,prior

def execute(cfg):
    assert WORK is not None
    cache=WORK/"cache"
    (cache/"tmp").mkdir(parents=True)
    env=dict(os.environ)
    env.update({"PDK_ROOT":str(PDK),"TMPDIR":str(cache/"tmp"),
                "XDG_CACHE_HOME":str(cache),
                "PYTHONNOUSERSITE":"1","PYTHONIOENCODING":"utf-8"})
    run_id="postgrt40-3x2-"+datetime.now().strftime("%Y%m%d-%H%M%S")
    cmd=[str(APP),"librelane","--pdk-root",str(PDK),
         "--pdk","sky130A","--scl","sky130_fd_sc_hd",
         "--flow","Classic","--jobs","2","--run-tag",run_id,str(cfg)]
    log=WORK/"physical-flow.log"
    show("INFO","LibreLane 3.0.17 local full RTL-to-GDS trial",
         f"Classic SKY130 HD, 2 jobs, run={run_id}")
    show("INFO","Full physical flow log",str(log))
    with log.open("w",encoding="utf-8") as out:
        try:
            r=subprocess.run(cmd,cwd=WORK,env=env,stdout=out,
                             stderr=subprocess.STDOUT,timeout=10800,check=False)
        except subprocess.TimeoutExpired:
            failure("Timeout after 10800 seconds; isolated trial artifacts retained")
    if r.returncode!=0:
        failure(f"LibreLane exited {r.returncode}; inspect preserved flow log")
    run=WORK/"src/runs"/run_id
    gds=run/"final/gds/tt_um_vaish_uart.gds"
    metrics=run/"final/metrics.json"
    if not gds.is_file() or gds.stat().st_size<4096 or not metrics.is_file():
        failure("LibreLane exited 0 but final GDS and metrics pair not found at config-local src/runs path")
    final=json_read(metrics,"New trial final metrics")
    if len(final)<200:
        failure(f"New final metrics incomplete: {len(final)} values")
    show("PASS","New trial 3x2 GDS",f"{gds} ({gds.stat().st_size} bytes)")
    show("INFO","New trial GDS SHA256",hash_file(gds))
    show("PASS","New final physical metrics",f"{len(final)} reported keys")
    return run,gds,metrics,final

def report(run,gds,mpath,new,old):
    assert WORK is not None
    for key in COMPARE:
        before=old.get(key,"NOT_REPORTED")
        after=new.get(key,"NOT_REPORTED")
        bad=(after=="NOT_REPORTED" or (isinstance(after,(int,float))
                 and after>0 and ("vio__count" in key or "drc" in key or "lvs_error" in key or "max_slew_violation" in key)))
        show("REVIEW" if bad else "METRIC",key,f"Stage3M={before}; Stage3P={after}")
    counts={}
    for corner in CORNERS:
        key="design__max_slew_violation__count__corner:"+corner
        b=old.get(key,"UNREPORTED")
        n=new.get(key,"UNREPORTED")
        counts[corner]={"stage3m":b,"stage3p":n}
        show("REVIEW" if n=="UNREPORTED" or n else "METRIC",
             "Max-slew "+corner,f"Stage3M={b}; Stage3P={n}")
    residual=[]
    for corner in ("nom_ss_100C_1v60","max_ss_100C_1v60"):
        reports=[]
        for p in run.rglob("checks.rpt"):
            if p.is_symlink() or not p.is_file() or p.stat().st_size>8*1024*1024:
                continue
            rel=p.relative_to(run)
            if corner in rel.parts and "stapostpnr" in rel.parts[0]:
                reports.append(p)
        if not reports:
            show("REVIEW","Saved postroute "+corner,"Missing checks.rpt")
            continue
        source=sorted(reports)[-1]
        entries=parse_report(source.read_text(encoding="utf-8",errors="replace"))
        emit_count=new.get("design__max_slew_violation__count__corner:"+corner)
        if emit_count!=len(entries):
            show("REVIEW","OpenSTA pin coverage "+corner,
                 f"metric {emit_count}; parsed {len(entries)} named pins")
        else:
            show("PASS","OpenSTA pin coverage "+corner,f"{len(entries)} named violations")
        for entry in entries[:8]:
            show("PIN","Remaining slew "+corner,
                 f"{entry['pin']} slew={entry['slew_ns']} ns, limit={entry['limit_ns']} ns, slack={entry['slack_ns']} ns")
        residual.append({"corner":corner,"report":str(source),"pins":entries})
    allzeros=all(new.get(k)==0 for k in (
        "route__drc_errors","magic__drc_error__count","klayout__drc_error__count",
        "design__lvs_error__count","timing__setup_vio__count",
        "timing__hold_vio__count","design__max_slew_violation__count"))
    if allzeros:
        show("PASS","Local checker bundle",
             "All seven key checkers report zero; NOT provider signoff")
    else:
        show("REVIEW","Local checker bundle",
             "At least one metric nonzero or unavailable; no timing closure claim")
    validate_hashes()
    show("PASS","Preserved original artifact hashes",
         "Stage3E/3M/2C/2F GDS, SDC and AppImage unchanged after new PnR")
    comparison={
        "scope":"Local 3x2 experimental PnR and DRC/LVS/STA comparison; not provider precheck",
        "stage3m_GDS_sha256":IMMUTABLE[1][1],
        "stage3p_GDS_sha256":hash_file(gds),
        "stage3p_GDS":str(gds),"stage3p_metrics":str(mpath),
        "change":"GRT_DESIGN_REPAIR_MAX_SLEW_PCT: 10 -> 40",
        "baseline_vs_new":{k:{"Stage3M":old.get(k),"Stage3P":new.get(k)}
                           for k in COMPARE},
        "all_corners":counts,"postroute_slew_reports":residual,
        "seven_checker_zeros":allzeros,
    }
    (WORK/"comparison.json").write_text(json.dumps(comparison,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    show("INFO","Complete comparison",str(WORK/"comparison.json"))
    show("INFO","Preserved Stage3P trial",str(WORK))
    show("INFO","Official Tiny Tapeout GDS Action/precheck",
         "NOT performed; production clock/IO/CDC and shuttle acceptance remain OPEN")

def main():
    try:
        cfg,old=preflight()
        run,gds,mpath,new=execute(cfg)
        report(run,gds,mpath,new,old)
        show("PASS","Stage3P local physical experiment",
             "Completed; metrics above determine actual repair effectiveness")
        print("===== END ASIC STAGE 3P =====",flush=True)
        summary()
    except Exception as exc:
        failure(f"{type(exc).__name__}: {exc}")

if __name__=="__main__":
    main()

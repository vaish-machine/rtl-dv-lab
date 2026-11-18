#!/usr/bin/env python3
r"""Stage 3M: isolated TT SKY130 3x2 physical slew-repair configuration trial.

The existing Stage 3E 3x2 local LibreLane run is immutable evidence. Copy
its four RTL sources, merged JSON configuration and pinned TT 3x2 DEF into a
NEW, G:-backed native WSL ext4 folder; apply conservative LibreLane resizer
settings and RUN_KLAYOUT_DRC=1, keeping 100 ns clock and existing 0.750 ns
slew limit. Run the local LibreLane 3.0.17 AppImage and compare actual final
metrics to the saved baseline. Never overwrite any previous design artifact.
Not the official Tiny Tapeout provider GDS Action or precheck.
"""
from __future__ import annotations

from datetime import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HOST=Path("/mnt/g/C-Drive-Backup-PreReset")
TEMP=HOST/"Temp"
TOOLS=Path("/home/vaish/DevTools/LibreLane")
BASE=TOOLS/"ttsky_sky130_3x2_slew_repair_trial"
OLD=TOOLS/"ttsky_sky130_3x2_trial/run-46NnPce8/template"
OLD_RUN=OLD/"src/runs/tt-3x2-20261116-123932"
OLD_GDS=OLD_RUN/"final/gds/tt_um_vaish_uart.gds"
OLD_METRICS=OLD_RUN/"final/metrics.json"
APP=TOOLS/"3.0.17/librelane-devshell-x86_64.AppImage"
PDK_ROOT=TOOLS/"pdks"
TT_DEF=OLD/"tt/tech/sky130A/def/tt_block_3x2_pg.def"
OLD2C=TOOLS/"uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
OLD2F=TOOLS/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
OLD_SDC=TOOLS/"uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc"
IMMUTABLE={
    OLD_GDS:"4ec93bad173dcf662bb45f8552e3fafaa35d94e5ccdabfdcd8e81a064387d599",
    OLD2C:"3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3",
    OLD2F:"d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af",
    OLD_SDC:"a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4",
    APP:"c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c",
}
FILES=("tt_um_vaish_uart.v","uart_core.sv","uart_tx.sv","uart_rx.sv")
RESULT_KEYS=(
    "design__max_slew_violation__count",
    "design__max_slew_violation__count__corner:nom_ss_100C_1v60",
    "design__max_slew_violation__count__corner:max_ss_100C_1v60",
    "route__drc_errors",
    "magic__drc_error__count",
    "klayout__drc_error__count",
    "design__lvs_error__count",
    "timing__setup_vio__count",
    "timing__hold_vio__count",
    "design__instance__area__stdcell",
    "design__instance__utilization__stdcell",
)
LINES=[]
WORK=None

def emit(level,field,message):
    row=f"{level} | {field} | {message}"
    LINES.append(row)
    print(row,flush=True)

def fail(reason):
    emit("FAIL","Stage 3M",reason)
    if WORK is not None:
        log=WORK/"physical-flow.log"
        if log.is_file():
            emit("INFO","Preserved full physical log",str(log))
            try:
                with log.open(encoding="utf-8",errors="replace") as f:
                    tail=f.readlines()[-100:]
                errors=[x.strip()[:300] for x in tail if
                        any(k in x.lower() for k in ("error", "fail", "fatal", "traceback","unknown key"))]
                for line in errors[-8:]:
                    emit("DIAG","Physical flow",line)
                for line in tail[-6:]:
                    emit("TAIL","Physical flow",line.strip()[:300])
            except OSError:
                pass
        emit("INFO","Preserved isolated trial",str(WORK))
    flush_summary()
    sys.exit(1)

def flush_summary():
    if TEMP.is_dir():
        stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
        path=TEMP/f"ASIC-Stage3M-TTSKY-3x2-Slew-Repair-{stamp}.txt"
        path.write_text("\n".join(LINES)+"\n",encoding="utf-8")
        print(f"INFO | G: summary | {path}",flush=True)

def check_file(path,label):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Missing or symlink {label}: {path}")
    return path

def checksum(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def check_hashes():
    for path,expected in IMMUTABLE.items():
        check_file(path,path.name)
        actual=checksum(path)
        if actual!=expected:
            raise RuntimeError(f"Existing input SHA256 changed: {path}: {actual}")
    emit("PASS","Immutable baseline","TT 3x2/Stage 2C/2F GDS, original SDC and AppImage SHA256 match")

def source_hashes():
    old_prov=json.loads(check_file(OLD/"LOCAL_TRIAL_PROVENANCE.json","Stage3E provenance").read_text())
    if old_prov.get("tile")!="3x2" or old_prov.get("provider_gds_precheck") is not False:
        raise RuntimeError("Incorrect Stage3E source provenance")
    hashes=old_prov.get("source_sha256",{})
    for name in FILES:
        source=check_file(OLD/"src"/name,name)
        if checksum(source)!=hashes.get(name):
            raise RuntimeError(f"Stage3E source does not match recorded provenance: {name}")
    emit("PASS","Four UART RTL source hashes","Exactly match preserved Stage3E provenance")

def prepare():
    global WORK
    if not TEMP.is_dir() or not TOOLS.is_dir() or getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root Ubuntu user vaish and G: Temp/G:-backed WSL tools")
    disk=shutil.disk_usage(HOST)
    if disk.free < 20*1024**3:
        raise RuntimeError(f"Insufficient G: free space: {disk.free/1024**3:.1f} GiB (<20 GiB)")
    emit("PASS","G: free storage",f"{disk.free/1024**3:.1f} GiB")
    check_hashes()
    source_hashes()
    oldm=json.loads(check_file(OLD_METRICS,"Stage3E original final metrics").read_text())
    if oldm.get("design__max_slew_violation__count")!=22 or len(oldm)<250:
        raise RuntimeError("Expected baseline 22 slew violations and full Stage3E metrics")
    check_file(TT_DEF,"Pinned TT 3x2 DEF")
    deftext=TT_DEF.read_text(encoding="utf-8")
    if "DIEAREA ( 0 0 ) ( 508760 225760 ) ;" not in deftext or "PINS 43 ;" not in deftext:
        raise RuntimeError("Official 3x2 DEF geometry/pins mismatch")
    previous=json.loads(check_file(OLD/"src/config_merged.json","Stage3E merged configuration").read_text())
    for key,value in {
        "DESIGN_NAME":"tt_um_vaish_uart",
        "DIE_AREA":"0 0 508.76 225.76",
        "FP_DEF_TEMPLATE":"dir::../tt/tech/sky130A/def/tt_block_3x2_pg.def",
        "CLOCK_PERIOD":100,
    }.items():
        if str(previous.get(key))!=str(value):
            raise RuntimeError(f"Original Stage3E configuration not expected: {key}")
    if previous.get("RUN_KLAYOUT_DRC") not in (0,False):
        raise RuntimeError("Original KLayout DRC was not disabled as observed")
    if previous.get("DESIGN_REPAIR_MAX_SLEW_PCT") is not None:
        emit("REVIEW","Existing slew repair margin",previous["DESIGN_REPAIR_MAX_SLEW_PCT"])
    BASE.mkdir(parents=True,exist_ok=True)
    WORK=Path(tempfile.mkdtemp(prefix="run-",dir=BASE))
    src=WORK/"src"
    src.mkdir()
    ref=WORK/"tt/tech/sky130A/def"
    ref.mkdir(parents=True)
    for name in FILES:
        shutil.copy2(OLD/"src"/name,src/name)
    shutil.copy2(TT_DEF,ref/TT_DEF.name)
    if checksum(ref/TT_DEF.name)!=checksum(TT_DEF):
        raise RuntimeError("Copied official TT DEF SHA256 mismatch")
    for name in FILES:
        if checksum(src/name)!=checksum(OLD/"src"/name):
            raise RuntimeError(f"Copied {name} differs from baseline")
    proposed=dict(previous)
    new_settings={
        "DEFAULT_CORNER":"max_ss_100C_1v60",
        "DESIGN_REPAIR_MAX_SLEW_PCT":30,
        "RUN_POST_GRT_DESIGN_REPAIR":True,
        "RUN_KLAYOUT_DRC":1,
    }
    proposed.update(new_settings)
    if proposed.get("MAX_TRANSITION_CONSTRAINT") != previous.get("MAX_TRANSITION_CONSTRAINT"):
        raise RuntimeError("Unexpected max transition constraint change")
    if proposed["CLOCK_PERIOD"]!=previous["CLOCK_PERIOD"]:
        raise RuntimeError("Unexpected clock period change")
    before={k:previous.get(k) for k in new_settings}
    cfg=src/"config_3m.json"
    cfg.write_text(json.dumps(proposed,indent=2)+"\n",encoding="utf-8")
    (WORK/"provenance.json").write_text(json.dumps({
        "scope":"Experimental LOCAL TT 3x2 max-slew repair; NOT provider GDS action",
        "baseline_GDS_SHA256":IMMUTABLE[OLD_GDS],
        "baseline_STD_CELL_AREA":oldm.get("design__instance__area__stdcell"),
        "baseline_max_slew":oldm["design__max_slew_violation__count"],
        "baseline_metrics":{k:oldm.get(k) for k in RESULT_KEYS},
        "previous_values":before,"trial_values":new_settings,
        "clock_period_ns":previous["CLOCK_PERIOD"],
        "max_transition_constraint_unchanged":True,
        "input_file_sha256":{p.name:checksum(p) for p in [cfg,ref/TT_DEF.name,*[src/f for f in FILES]]},
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit("PASS","Fresh isolated G:-backed 3x2 workspace",str(WORK))
    emit("PASS","Trial knobs","Worst SS repair corner, slew margin 30%, post-GRT repair, KLayout DRC enabled")
    emit("PASS","Provisional 100 ns clock","Unchanged; no weakening of 0.750 ns reported slew limit")
    return cfg,oldm

def perform(cfg):
    assert WORK is not None
    env=dict(os.environ)
    cache=WORK/"cache"
    (cache/"tmp").mkdir(parents=True)
    env.update({
        "PDK_ROOT":str(PDK_ROOT),
        "TMPDIR":str(cache/"tmp"),
        "XDG_CACHE_HOME":str(cache),
        "PYTHONNOUSERSITE":"1",
        "PYTHONIOENCODING":"utf-8",
    })
    tag="slewfix-3x2-"+datetime.now().strftime("%Y%m%d-%H%M%S")
    log=WORK/"physical-flow.log"
    cmd=[
        str(APP),"librelane","--pdk-root",str(PDK_ROOT),
        "--pdk","sky130A","--scl","sky130_fd_sc_hd",
        "--flow","Classic","--jobs","2","--run-tag",tag,str(cfg),
    ]
    emit("INFO","Local LibreLane 3.0.17 physical-flow trial",f"Classic SKY130 HD, 2 jobs, tag={tag}")
    emit("INFO","Full G:-backed flow log",str(log))
    with log.open("w",encoding="utf-8") as stream:
        try:
            result=subprocess.run(cmd,cwd=WORK,env=env,stdout=stream,stderr=subprocess.STDOUT,
                                  timeout=10800,check=False)
        except subprocess.TimeoutExpired:
            fail("LibreLane exceeded 10800-second runtime limit, evidence retained")
    if result.returncode!=0:
        fail(f"LibreLane returned nonzero exit {result.returncode}; see preserved physical-flow.log")
    run=WORK/"src/runs"/tag
    gds=run/"final/gds/tt_um_vaish_uart.gds"
    mpath=run/"final/metrics.json"
    if not gds.is_file() or gds.stat().st_size<4096 or not mpath.is_file():
        fail("LibreLane exited 0 but expected final GDS/metrics pair not at config-local src/runs path")
    emit("PASS","Trial final GDS created",f"{gds} ({gds.stat().st_size} bytes)")
    emit("INFO","Trial GDS SHA256",checksum(gds))
    metrics=json.loads(mpath.read_text(encoding="utf-8"))
    if len(metrics)<200:
        fail(f"Final metrics unexpectedly incomplete: {len(metrics)} entries")
    return gds,mpath,metrics

def report_results(gds,mpath,metrics,baseline):
    assert WORK is not None
    emit("PASS","New trial metrics",f"{len(metrics)} metric keys")
    for k in RESULT_KEYS:
        old,new=baseline.get(k,"MISSING"),metrics.get(k,"MISSING")
        flag="REVIEW" if new=="MISSING" else "METRIC"
        if "vio__count" in k or "drc_error" in k or "drc_errors" in k or "lvs_error" in k or "max_slew_violation" in k:
            if new!="MISSING" and new!=0: flag="REVIEW"
        emit(flag,k,f"baseline={old}; trial={new}")
    slew=metrics.get("design__max_slew_violation__count")
    if slew==0:
        emit("PASS","Experimental max-slew closure","Zero aggregate slew violations reported in trial")
    else:
        emit("REVIEW","Experimental max-slew closure",f"Not closed: trial count={slew}")
    klayout=metrics.get("klayout__drc_error__count")
    if klayout is None:
        emit("REVIEW","KLayout DRC","Enabled in config, but metric NOT reported; no DRC pass claim")
    elif klayout==0:
        emit("PASS","Trial KLayout DRC metric","0 violations reported")
    else:
        emit("REVIEW","Trial KLayout DRC metric",f"{klayout} reported violations")
    checklist=(
        "route__drc_errors","magic__drc_error__count","design__lvs_error__count",
        "timing__setup_vio__count","timing__hold_vio__count",
        "design__max_slew_violation__count","klayout__drc_error__count",
    )
    good=all(metrics.get(k)==0 for k in checklist)
    emit("PASS" if good else "REVIEW","Local trial checker bundle",
         "All seven reported zeros" if good else "Not all seven checkers reported zero; investigate before proceeding")
    check_hashes()
    emit("PASS","Post-trial original hashes","Baseline TT/Stage2C/Stage2F GDS, SDC, AppImage unchanged")
    emit("INFO","Experimental only","Not real TT GDS Action, provider precheck, production clock/IO/CDC signoff, or tile purchase")
    (WORK/"comparison.json").write_text(json.dumps({
        "scope":"New exploratory local 3x2 PnR, not provider physical acceptance",
        "baseline_gds_sha256":IMMUTABLE[OLD_GDS],
        "trial_gds_sha256":checksum(gds),"trial_gds":str(gds),
        "trial_metrics":str(mpath),
        "before_after":{k:{"baseline":baseline.get(k),"trial":metrics.get(k)} for k in RESULT_KEYS},
        "all_reported_zero":good,
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit("INFO","Complete G:-backed comparison",str(WORK/"comparison.json"))
    emit("INFO","Preserved new trial folder",str(WORK))
    emit("INFO","Official TT provider precheck","OPEN even if local trial checkers pass")

def main():
    print("===== ASIC STAGE 3M: ISOLATED TTSKY 3X2 SLEW REPAIR AND KLAYOUT DRC TRIAL =====",flush=True)
    try:
        cfg,base=prepare()
        newgds,mpath,metrics=perform(cfg)
        report_results(newgds,mpath,metrics,base)
        emit("PASS","Stage 3M local physical trial","Completed; interpret each actual metric above, no automatic signoff")
        print("===== END ASIC STAGE 3M =====",flush=True)
        flush_summary()
    except Exception as exc:
        fail(f"{type(exc).__name__}: {exc}")

if __name__=="__main__":
    main()

#!/usr/bin/env python3
r"""ASIC Stage 2K: READ-ONLY unconstrained-path endpoint and check_setup audit.

Read the existing Stage 2F UART 9-corner OpenSTA checks.rpt files and the
original pinned provisional SDC. Extract full saved report sections,
then show compact startpoint/endpoint/path groups and a representative
source excerpt. Do not run STA, Git or EDA; do not alter layout or RTL.
Outputs only to G:\C-Drive-Backup-PreReset\Temp.
"""
from __future__ import annotations

from datetime import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys

HOST = Path("/mnt/g/C-Drive-Backup-PreReset")
TEMP = HOST / "Temp"
BASE = Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x")
RUN = BASE / "runs/sdc-explore-20261116-074159"
OLD = Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
GDS = RUN / "final/gds/uart_core.gds"
SDC = BASE / "src/uart_10mhz_provisional.sdc"
CFG = RUN / "resolved.json"
PROV = BASE / "PROVENANCE.txt"
METRICS = RUN / "final/metrics.json"
GOLD_SHA = "3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
GDS_SHA = "d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
SDC_SHA = "a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4"
SOURCE_REV = "712be2f718757d55f6aa7ab154d05f8d050bacac"
MAX_FILE_BYTES = 8 * 1024 * 1024
COMMANDS = [
    ("unconstrained", re.compile(r"^\s*report_checks\s+-unconstrained\s*$")),
    ("negative_slack", re.compile(r"^\s*report_checks\s+--slack_max\s+-0\.01\s*$")),
    ("electrical", re.compile(r"^\s*report_check_types\s+-max_slew\b")),
    ("annotation", re.compile(r"^\s*report_parasitic_annotation\s+-report_unannotated\s*$")),
    ("check_setup", re.compile(r"^\s*check_setup\s+-verbose\b")),
]
INTERESTING = re.compile(
    r"(?i)(Startpoint:|Endpoint:|Path Group:|Path Type:|slack\b|"
    r"clock\b|input external delay|output external delay|"
    r"data arrival time|data required time|unconstrained|"
    r"no paths found|^warning\b|^error\b|^no_)"
)
lines_out = []

def say(level, name, result):
    value = f"{level} | {name} | {result}"
    print(value, flush=True)
    lines_out.append(value)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while buffer := stream.read(1024 * 1024):
            h.update(buffer)
    return h.hexdigest()

def required(path, label):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} missing or symlink: {path}")

def parse_sections(path):
    required(path, "STA checks.rpt")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise RuntimeError(f"Report too large to inspect safely: {path}")
    original = path.read_text(encoding="utf-8", errors="replace").splitlines()
    positions = []
    for i, raw in enumerate(original):
        for name, regex in COMMANDS:
            if regex.match(raw):
                positions.append((i,name))
                break
    names = [name for _,name in positions]
    if names != [name for name,_ in COMMANDS]:
        raise RuntimeError(f"Report section format differs from LibreLane 3.0.17: {path} / {names}")
    result={}
    for idx,(start,name) in enumerate(positions):
        end=positions[idx+1][0] if idx+1<len(positions) else len(original)
        numbered = [(i+1, original[i]) for i in range(start+1,end)]
        content = []
        for n,raw in numbered:
            stripped=raw.strip()
            if not stripped or re.fullmatch(r"=+",stripped) or re.match(r"=+.*Corner.*=+",stripped):
                continue
            content.append({"line":n,"text":stripped[:500]})
        relevant=[row for row in content if INTERESTING.search(row["text"])]
        starts=[row for row in content if row["text"].startswith("Startpoint:")]
        ends=[row for row in content if row["text"].startswith("Endpoint:")]
        groups=[row for row in content if row["text"].startswith(("Path Group:","Path Type:"))]
        no_paths=[row for row in content if "No paths found" in row["text"]]
        result[name]={
            "command_line":start+1,
            "first_line":start+2,
            "last_line":end,
            "startpoints":starts[:40],
            "endpoints":ends[:40],
            "groups":groups[:30],
            "no_paths":no_paths[:10],
            "relevant":relevant[:120],
            "body":content[:160],
        }
    return result

def main():
    print("===== ASIC STAGE 2K: UART UNCONSTRAINED PATH ENDPOINT REVIEW =====",flush=True)
    if getpass.getuser() != "vaish" or os.geteuid() == 0:
        raise RuntimeError("Expected non-root WSL Ubuntu user vaish")
    if not TEMP.is_dir():
        raise RuntimeError("G: Temp not mounted")
    for name,path,expected in (
        ("Original Stage 2C GDS",OLD,GOLD_SHA),
        ("Stage 2F GDS",GDS,GDS_SHA),
        ("Applied Stage 2F SDC",SDC,SDC_SHA),
    ):
        required(path,name)
        if digest(path) != expected:
            raise RuntimeError(f"{name} SHA256 mismatch; stopping")
        say("PASS",name,"SHA256 matches preserved baseline")
    for path in (CFG,PROV,METRICS):
        required(path,path.name)
    if f"Git HEAD: {SOURCE_REV}" not in PROV.read_text(encoding="utf-8"):
        raise RuntimeError("Source revision mismatch")
    say("PASS","Source provenance",SOURCE_REV)
    cfg=json.loads(CFG.read_text(encoding="utf-8"))
    metrics=json.loads(METRICS.read_text(encoding="utf-8"))
    if not isinstance(cfg,dict) or not isinstance(metrics,dict) or len(metrics)!=307:
        raise RuntimeError("Unexpected resolved configuration or metrics")
    for field in ("PNR_SDC_FILE","SIGNOFF_SDC_FILE"):
        val=cfg.get(field)
        if not isinstance(val,str):
            raise RuntimeError(f"{field} missing")
        candidate=Path(val)
        if not candidate.is_absolute(): candidate=BASE/candidate
        if candidate.resolve(strict=True)!=SDC.resolve(strict=True):
            raise RuntimeError(f"{field} not pinned to expected SDC")
    say("PASS","Resolved SDC","PNR and signoff match pinned 100 ns experimental SDC")
    sta_dirs=[p for p in RUN.iterdir()
              if p.is_dir() and "openroad-stapostpnr" in p.name.lower()]
    if len(sta_dirs)!=1:
        raise RuntimeError(f"Expected 1 postroute STA step dir, found {len(sta_dirs)}")
    corners=sorted(p for p in sta_dirs[0].iterdir() if p.is_dir())
    if len(corners)!=9:
        raise RuntimeError(f"Expected 9 corner directories; found {len(corners)}")
    evidence=[]
    all_start=[]
    all_end=[]
    check_setup_warnings=0
    sample=None
    for corner in corners:
        sections=parse_sections(corner/"checks.rpt")
        u=sections["unconstrained"]
        n=sections["negative_slack"]
        check=sections["check_setup"]
        starts=[e["text"] for e in u["startpoints"]]
        ends=[e["text"] for e in u["endpoints"]]
        all_start+=starts
        all_end+=ends
        if "max_ss_100C_1v60" == corner.name:
            sample=(corner.name,u,check)
        say("REPORT",corner.name,
            f"unconstrained={len(starts)} start / {len(ends)} end, "
            f"negative-slack no-paths={len(n['no_paths'])}, "
            f"check_setup relevant lines={len(check['relevant'])}")
        if starts or ends:
            say("PATH",corner.name,
                f"{starts[0] if starts else 'Startpoint missing'} -> "
                f"{ends[0] if ends else 'Endpoint missing'}")
        else:
            say("REVIEW",corner.name,"No endpoint or startpoint detail extracted")
        if u["groups"]:
            say("PATHGROUP",corner.name,
                "; ".join(x["text"] for x in u["groups"][:2]))
        # Exclude the check_setup command echo, but preserve genuine warning/status
        # lines to distinguish header text from actual diagnostics.
        warnings=[x for x in check["body"]
                  if re.search(r"(?i)^(warning|error|no\s+(clock|input|output|generated)|unconstrained\s+\w+)",x["text"])]
        check_setup_warnings+=len(warnings)
        if warnings:
            say("REVIEW",corner.name,"check_setup: "+warnings[0]["text"][:160])
        evidence.append({
            "corner":corner.name,"sections":sections,
            "check_setup_status_lines":warnings[:45],
            "actual_worst_setup_slack_ns":metrics.get(f"timing__setup__ws__corner:{corner.name}"),
            "actual_worst_hold_slack_ns":metrics.get(f"timing__hold__ws__corner:{corner.name}"),
        })
    if sample:
        corner,u,check=sample
        say("INFO","Representative unconstrained-path excerpt",
            f"{corner} from checks.rpt; full 9-corner bodies stored in JSON")
        # 22 lines of the actual report excerpt, rather than inferred diagnosis.
        for line in u["body"][:24]:
            say("CONTEXT",f"L{line['line']}",line["text"][:180])
        if check_setup_warnings:
            say("INFO","Representative check_setup status",
                f"{len(check['body'])} body lines saved; warnings across corners={check_setup_warnings}")
            for line in check["body"][:12]:
                say("CHECK_SETUP",f"L{line['line']}",line["text"][:180])
    say("INFO","Distinct unconstrained endpoints",
        str(len(set(all_end)))+" distinct endpoint descriptions across 9 corners")
    for endpoint in sorted(set(all_end))[:8]:
        say("ENDPOINT",endpoint,"Found in unconstrained report")
    if any(all_start) or any(all_end):
        say("REVIEW","Timing coverage",
            "At least one unconstrained STA path remains; do not add an exception without endpoint analysis")
    say("INFO","Timing limits",
        "Provisional 100 ns clock, 0-10 ns external delays; no real board/wrapper timing signoff")
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    output=TEMP/f"ASIC-Stage2K-UART-Unconstrained-Details-{stamp}.json"
    short=TEMP/f"ASIC-Stage2K-UART-Unconstrained-Summary-{stamp}.txt"
    output.write_text(json.dumps({
        "scope":"Read-only constrained UART STA path inspection, NOT signoff",
        "script_revision":"Stage2K",
        "old_gds":GOLD_SHA,"new_gds":GDS_SHA,
        "sdc_sha256":SDC_SHA,"rtl_commit":SOURCE_REV,
        "unique_unconstrained_startpoint_descriptions":sorted(set(all_start)),
        "unique_unconstrained_endpoint_descriptions":sorted(set(all_end)),
        "corners":evidence,
    },indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    say("PASS","Read-only Stage 2K inspection","Saved original report excerpts only; no design changes")
    say("INFO","Full evidence JSON",str(output))
    say("INFO","Compact G: summary",str(short))
    short.write_text("\n".join(lines_out)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 2K =====",flush=True)

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL | Stage 2K audit | {type(exc).__name__}: {exc}",file=sys.stderr)
        sys.exit(1)

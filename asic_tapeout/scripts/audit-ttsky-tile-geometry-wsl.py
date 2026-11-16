#!/usr/bin/env python3
r"""ASIC Stage 3D — read-only official SKY130 tile geometry feasibility audit.

Download only the pinned TinyTapeout tt-support-tools SKY130 tile dimension
list and corresponding DEF geometry, compare with previously recorded
standalone Stage 2F RTL-to-GDS metrics, verify Stage 3C cocotb XML.
This is NOT an actual TT physical implementation or proof of tile fit.
No design/source/GDS/SDC mutation, no provider CI/GDS/precheck, no payment.
All new files are under G:-backed native Ubuntu ext4 or G:\...\Temp.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import urlopen, Request
import xml.etree.ElementTree as ET

TEMP = Path("/mnt/g/C-Drive-Backup-PreReset/Temp")
NATIVE = Path("/home/vaish/DevTools/LibreLane/ttsky_tile_geometry_audit")
STAGE3C = Path("/home/vaish/DevTools/LibreLane/ttsky_official_template_cocotb/run-i1DErq6p/template")
REPO = Path("/home/vaish/projects/rtl-dv-lab")
RUN2F = Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159")
ORIG = Path("/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds")
NEW = RUN2F / "final/gds/uart_core.gds"
METRICS = RUN2F / "final/metrics.json"
SDC = Path("/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/src/uart_10mhz_provisional.sdc")
SHA2C = "3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
SHA2F = "d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
SDC_SHA = "a392f38145b384f86049925902721389a769e20273ab4e1d9d99cc0c9466ffc4"
TT_TEMPLATE = "a42e6662fab316e93b4e26399e21d41664a460b7"
TT_TOOLS = "9d13ff3e3e6202090740110438c6a10c1d62ca0f"
SOURCE_FILES = ("uart_tx.sv", "uart_rx.sv", "uart_core.sv", "tt_um_vaish_uart.v")
TILE_TYPES = ("1x1", "1x2", "2x2", "3x2", "4x2", "6x2", "8x2")
URL = "https://raw.githubusercontent.com/TinyTapeout/tt-support-tools/" + TT_TOOLS + "/tech/sky130A/"
LOG = []

def emit(kind, what, value):
    line = f"{kind} | {what} | {value}"
    print(line, flush=True)
    LOG.append(line)

def must_file(p, label):
    if not p.is_file() or p.is_symlink():
        raise RuntimeError(f"{label} missing or symlink: {p}")
    return p

def hash_file(p):
    h = hashlib.sha256()
    with p.open("rb") as stream:
        while b := stream.read(1024 * 1024):
            h.update(b)
    return h.hexdigest()

def hash_pin(p, expected, label):
    must_file(p, label)
    actual = hash_file(p)
    if actual != expected:
        raise RuntimeError(f"{label} SHA256 mismatch: {actual}")
    emit("PASS", label, "SHA256 preserved")

def native_workspace():
    if not NATIVE.parent.is_dir():
        raise RuntimeError("Expected G:-backed WSL LibreLane directory missing")
    NATIVE.mkdir(exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="geometry-", dir=NATIVE))
    emit("PASS", "Isolated G:-backed workspace", str(workspace))
    return workspace

def retrieve(relative, workspace):
    target = workspace / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    request = Request(URL + relative, headers={"User-Agent": "ASIC-Stage3D-reproducible-tile-audit"})
    with urlopen(request, timeout=45) as response:
        contents = response.read(1024 * 1024 + 1)
    if len(contents) > 1024 * 1024:
        raise RuntimeError(f"Provider reference exceeds 1MiB: {relative}")
    target.write_bytes(contents)
    return contents.decode("utf-8"), hash_file(target)

def parse_sizes(text):
    out = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        m = re.fullmatch(r'\s*(\dx\d):\s*"0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"\s*', line)
        if m is None:
            raise RuntimeError("Unexpected official SKY tile_sizes.yaml line: " + line[:120])
        out[m.group(1)] = (Decimal(m.group(2)), Decimal(m.group(3)))
    if any(t not in out for t in TILE_TYPES):
        raise RuntimeError("Provider's required template tile shapes missing from SKY geometry")
    return out

def verify_def(text, title, width, height):
    units = re.search(r"(?m)^UNITS DISTANCE MICRONS\s+(\d+)\s*;\s*$", text)
    box = re.search(
        r"(?m)^DIEAREA\s*\(\s*0\s+0\s*\)\s*\(\s*(\d+)\s+(\d+)\s*\)\s*;\s*$",text
    )
    if not units or not box:
        raise RuntimeError(f"Provider DEF geometry missing for tile {title}")
    scale = Decimal(units.group(1))
    x = Decimal(box.group(1)) / scale
    y = Decimal(box.group(2)) / scale
    if (x, y) != (width, height):
        raise RuntimeError(f"DEF/yaml geometry disagreement for {title}: {x},{y}")
    if "PINS 43" not in text:
        raise RuntimeError(f"Unexpected SKY digital macro pin template for tile {title}")
    return {"die_um": [str(x), str(y)], "units_per_micron": str(scale), "pins": 43}

def verify_cocotb_test():
    base = STAGE3C
    result = must_file(base / "test/results.xml", "Stage 3C cocotb results.xml")
    root = ET.parse(result).getroot()
    cases = root.findall(".//testcase")
    if not cases:
        raise RuntimeError("Stage 3C XML has no testcases")
    failed = [x for x in cases if x.find("failure") is not None or x.find("error") is not None]
    skipped = [x for x in cases if x.find("skipped") is not None]
    if failed or skipped:
        raise RuntimeError(f"Stage 3C XML has failed={len(failed)}, skipped={len(skipped)}")
    info = must_file(base / "info.yaml", "Stage 3C source metadata").read_text(encoding="utf-8")
    if 'top_module: "tt_um_vaish_uart"' not in info:
        raise RuntimeError("Saved Stage 3C top module unexpectedly changed")
    if 'tiles: "1x1"' not in info or "PLACEHOLDER" not in info:
        raise RuntimeError("Expected unverified 1x1 template placeholder absent")
    for name in SOURCE_FILES:
        local = base / "src" / name
        original = REPO / "asic_tapeout" / ("shuttle/ttsky_candidate/src" if name=="tt_um_vaish_uart.v" else "rtl") / name
        must_file(local, "Stage 3C UART " + name)
        must_file(original, "Original UART RTL " + name)
        if hash_file(local) != hash_file(original):
            raise RuntimeError("Original UART source differs from successful cocotb copy: " + name)
    if not (base/".git").is_dir():
        raise RuntimeError("Expected official template Git metadata missing")
    actual = subprocess.check_output(["git","-C",str(base),"rev-parse","HEAD"],text=True).strip()
    if actual != TT_TEMPLATE:
        raise RuntimeError("Stage 3C official template revision mismatch " + actual)
    emit("PASS", "Stage 3C source, template and cocotb XML", f"{len(cases)} testcase(s), no failures or skips")
    return {"testcases":len(cases), "xml":str(result), "official_template_commit":actual}

def main():
    print("===== ASIC STAGE 3D: SKY130 OFFICIAL TILE GEOMETRY FEASIBILITY =====", flush=True)
    if getpass.getuser()!="vaish" or os.geteuid()==0:
        raise RuntimeError("Expected non-root Ubuntu user vaish")
    if not TEMP.is_dir():
        raise RuntimeError("G: Temp not mounted")
    hash_pin(ORIG,SHA2C,"Original Stage 2C GDS")
    hash_pin(NEW,SHA2F,"Original Stage 2F GDS")
    hash_pin(SDC,SDC_SHA,"Applied Stage 2F provisional SDC")
    passed = verify_cocotb_test()
    metrics=json.loads(must_file(METRICS,"Stage 2F final metrics").read_text(encoding="utf-8"))
    if not isinstance(metrics,dict) or len(metrics)!=307:
        raise RuntimeError("Unexpected Stage 2F metric source")
    area_raw=metrics.get("design__instance__area")
    try:
        area = Decimal(str(area_raw))
    except (InvalidOperation, ValueError) as e:
        raise RuntimeError("Standalone instance area missing or non-numeric") from e
    if area <= 0:
        raise RuntimeError("Standalone instance area must be positive")
    emit("METRIC","Stage 2F standalone reported instance area",f"{area} um^2; NOT a fresh TT wrapper synthesis measurement")
    workspace=native_workspace()
    size_source,size_hash=retrieve("tile_sizes.yaml",workspace)
    dims=parse_sizes(size_source)
    emit("PASS","Official TT SKY tile-size source",f"tt-support-tools @{TT_TOOLS[:12]}, SHA256 {size_hash}")
    comparison={}
    for name in TILE_TYPES:
        width,height=dims[name]
        path=f"def/tt_block_{name}_pg.def"
        def_text,def_sha=retrieve(path,workspace)
        definfo=verify_def(def_text,name,width,height)
        rectangle=width*height
        percent=(area/rectangle)*Decimal(100)
        # Old standalone macro vs new TT wrapper is NOT a 1:1 synthesis
        # comparison. This is a screening benchmark, not a physical fit.
        flag="REFERENCE AREA ABOVE DIE RECTANGLE" if area>=rectangle else "UNPROVEN CAPACITY"
        comparison[name]={
            "width_um":str(width),"height_um":str(height),
            "die_area_um2":str(rectangle),
            "standalone_instance_area_percent_of_die":str(percent.quantize(Decimal("0.01"))),
            "flag":flag,
            "def_sha256":def_sha, "def_properties":definfo,
        }
        emit("GEOMETRY",name,
             f"{width}x{height} um, area={rectangle} um^2; "
             f"old instance-area benchmark={percent:.1f}%; {flag}")
    if area >= dims["1x1"][0]*dims["1x1"][1]:
        emit("REVIEW","1x1 placeholder",
             "Earlier standalone cell-area proxy exceeds official die rectangle; do not assume default tile fits")
    emit("INFO","Suggested next physical work",
         "Trial provider-specific hardening at a tile allocation agreed for exploration; 2x2/3x2 are NOT certified fits")
    emit("INFO","Critical limitations",
         "Old macro instances include filler/repair; wrapper and provider floorplan/synthesis differ. No tile proves fit until full provider GDS/precheck")
    emit("INFO","No shuttle action",
         "No provider CI, harden, template repository creation, slot reservation, cost or submission")
    stamped=datetime.now().strftime("%Y%m%d-%H%M%S")
    full=TEMP/f"ASIC-Stage3D-TTSKY-Tile-Geometry-{stamped}.json"
    short=TEMP/f"ASIC-Stage3D-TTSKY-Geometry-Summary-{stamped}.txt"
    body={
        "scope":"READ-ONLY dimensional SCREENING; not official TT tile fit/physical signoff",
        "tt_support_tools_commit":TT_TOOLS,
        "tt_tile_sizes_sha256":size_hash,
        "tt_source_url":URL,
        "stage3c":passed,
        "standalone_stage2f_metric_source":str(METRICS),
        "standalone_stage2f_instance_area_um2":str(area),
        "tile_shapes":comparison,
        "reference_files_workspace":str(workspace),
        "source_GDS_sha256":SHA2F,
        "old_GDS_sha256":SHA2C,
        "SDC_sha256":SDC_SHA,
    }
    full.write_text(json.dumps(body,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit("PASS","Stage 3D geometry evidence",
         "All official tile dimensions crosschecked against provider DEF; original design untouched")
    emit("INFO","Detailed G: geometry JSON",str(full))
    emit("INFO","Compact G: audit",str(short))
    short.write_text("\n".join(LOG)+"\n",encoding="utf-8")
    print("===== END ASIC STAGE 3D =====", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL | Stage 3D | {type(error).__name__}: {error}",file=sys.stderr)
        sys.exit(1)

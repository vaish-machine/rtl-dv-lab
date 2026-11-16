#!/usr/bin/env bash
# Stage 3C: run the official-template UART cocotb RTL simulation locally.
# Python venv, pip cache, temporary files and template copy remain on G:-backed WSL ext4.
# Never invokes provider GDS/CI, purchases a slot, or modifies existing RTL/GDS.
set -Eeuo pipefail

ROOT="/mnt/g/C-Drive-Backup-PreReset"
TEMP="$ROOT/Temp"
REPO="/home/vaish/projects/rtl-dv-lab"
BASE="/home/vaish/DevTools/LibreLane/ttsky_official_template_cocotb"
SOURCE="/home/vaish/DevTools/LibreLane/ttsky_official_template_dryrun/ttsky-Lc4FY5ix/template"
TEMPLATE_REV="a42e6662fab316e93b4e26399e21d41664a460b7"
GDS2C="/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
GDS2F="/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
SHA2C="3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
SHA2F="d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"

echo "===== ASIC STAGE 3C: TTSKY LOCAL COCOTB UART RTL TEST ====="
if [[ ! -d "$TEMP" ]]; then
    echo "FAIL | G: Temp directory missing; no files modified"
    exit 1
fi
LOG="$TEMP/ASIC-Stage3C-TTSKY-Cocotb-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
WORK=""
say() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >>"$LOG"
}
fail() {
    say FAIL "$1" "$2"
    if [[ -n "$WORK" ]]; then
        for file in "$WORK/venv.log" "$WORK/pip.log" "$WORK/template-check.log" "$WORK/cocotb.log" "$WORK/results-check.log"; do
            if [[ -s "$file" ]]; then
                echo "INFO | Detailed diagnosis in: $file"
                tail -n 13 "$file" || true
            fi
        done
        say INFO "Preserved G:-backed workspace" "$WORK"
    fi
    say INFO "Detailed G: summary" "$LOG"
    exit 1
}
verify_gds() {
    local file="$1" expected="$2" observed
    [[ -f "$file" && ! -L "$file" ]] ||
        fail "GDSII preservation" "Original GDS missing or symlink: $file"
    observed="$(sha256sum "$file" | awk '{print $1}')"
    [[ "$observed" == "$expected" ]] ||
        fail "GDSII preservation" "SHA256 mismatch on $file"
}
[[ "$(id -un)" == "vaish" && "$(id -u)" != "0" ]] ||
    fail "Linux user" "Expected Ubuntu user vaish (non-root)"
for program in git python3 iverilog make timeout df awk sha256sum mktemp cp; do
    command -v "$program" >/dev/null 2>&1 ||
        fail "Prerequisite" "Required command unavailable: $program"
done
[[ -d "$REPO/.git" ]] ||
    fail "Repository" "Expected WSL local rtl-dv-lab checkout missing"
[[ "$(git -C "$REPO" branch --show-current)" == main ]] ||
    fail "Repository" "Expected branch main"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] ||
    fail "Repository" "Unexpected Git origin"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] ||
    fail "Repository" "Local edits detected; no pull attempted"
git -C "$REPO" fetch origin main >>"$LOG" 2>&1 ||
    fail "Git fetch" "Could not fetch origin/main; no pull attempted"
git -C "$REPO" merge-base --is-ancestor HEAD origin/main ||
    fail "Git fast-forward" "Divergent Git history; no pull attempted"
git -C "$REPO" merge --ff-only origin/main >>"$LOG" 2>&1 ||
    fail "Git fast-forward" "Failed to fast-forward clean main"
say PASS "Git fast-forward" "$(git -C "$REPO" rev-parse HEAD)"
verify_gds "$GDS2C" "$SHA2C"
verify_gds "$GDS2F" "$SHA2F"
say PASS "Original Stage 2C and 2F GDSII" "Both SHA256 values unchanged"

[[ -d "$SOURCE/.git" && -f "$SOURCE/test/test.py" && -f "$SOURCE/test/Makefile" ]] ||
    fail "Stage 3B template" "Successful Stage 3B template missing: $SOURCE"
[[ "$(git -C "$SOURCE" rev-parse HEAD)" == "$TEMPLATE_REV" ]] ||
    fail "Official template pin" "Copied Stage 3B template is not at pinned revision"
FREE_KB="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
[[ "$FREE_KB" =~ ^[0-9]+$ && "$FREE_KB" -ge 5242880 ]] ||
    fail "G: capacity" "Less than 5 GiB available"
say PASS "G: free storage" "$((FREE_KB / 1048576)) GiB"
mkdir -p "$BASE"
WORK="$(mktemp -d "$BASE/run-XXXXXXXX")"
mkdir -p "$WORK/tmp" "$WORK/cache"
export TMPDIR="$WORK/tmp"
export XDG_CACHE_HOME="$WORK/cache"
export PIP_CACHE_DIR="$WORK/cache/pip"
export PYTHONNOUSERSITE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
say PASS "Isolated G:-backed workspace" "$WORK"
cp -a "$SOURCE" "$WORK/template" ||
    fail "Copy official Stage 3B template" "Failed to stage independent source copy"
# Confirm all local test prerequisites before installing Python-only packages.
if ! python3 - "$WORK/template" "$REPO" >"$WORK/template-check.log" 2>&1 <<'PY'
from pathlib import Path
import re
import sys
p=Path(sys.argv[1])
r=Path(sys.argv[2])
requirements=(p/"test/requirements.txt").read_text(encoding="utf-8")
assert requirements.splitlines()==["pytest==8.4.2","cocotb==2.1.0"], requirements
tb=(p/"test/tb.v").read_text(encoding="utf-8")
assert "tt_um_vaish_uart user_project" in tb
assert "tt_um_example user_project" not in tb
make=(p/"test/Makefile").read_text(encoding="utf-8")
expected="PROJECT_SOURCES = tt_um_vaish_uart.v uart_core.sv uart_tx.sv uart_rx.sv"
assert expected in make, make
assert "COCOTB_TEST_MODULES = test" in make
yaml=(p/"info.yaml").read_text(encoding="utf-8")
assert 'top_module: "tt_um_vaish_uart"' in yaml
assert 'tiles: "1x1"' in yaml
assert "PLACEHOLDER" in yaml
assert "yaml_version: 6" in yaml
expected_sources={"uart_tx.sv","uart_rx.sv","uart_core.sv","tt_um_vaish_uart.v"}
assert set(re.findall(r'(?m)^    - "([^"]+)"\s*$',yaml))==expected_sources
for name in expected_sources:
    actual=p/"src"/name
    origin=(r/"asic_tapeout/shuttle/ttsky_candidate/src"/name
            if name=="tt_um_vaish_uart.v" else r/"asic_tapeout/rtl"/name)
    assert actual.is_file() and origin.is_file(), name
    assert actual.read_bytes()==origin.read_bytes(), f"Copied RTL differs: {name}"
assert (p/"test/test.py").read_bytes()==(r/"asic_tapeout/shuttle/ttsky_candidate/test/test.py").read_bytes()
print("PASS | Copied Stage 3B template | sources, metadata, cocotb and official harness match Git")
PY
then
    fail "Template input verification" "See template-check.log"
fi
say PASS "Pinned official template copy" "Original provider testbench, UART sources and cocotb module verified"
if ! python3 -m venv "$WORK/venv" >"$WORK/venv.log" 2>&1; then
    fail "Python virtual environment" "python3 -m venv unavailable; no global/system changes attempted"
fi
VENV="$WORK/venv"
if ! "$VENV/bin/python" -m pip --version >>"$WORK/venv.log" 2>&1; then
    fail "Virtualenv pip" "venv was created without pip; no system Python modified"
fi
say PASS "Python venv" "Created independently under G:-backed WSL ext4"
if ! timeout 300s "$VENV/bin/python" -m pip install --no-input \
    --only-binary=:all: -r "$WORK/template/test/requirements.txt" \
    >"$WORK/pip.log" 2>&1; then
    fail "Local cocotb package setup" "Pinned Python requirements install failed; see pip.log"
fi
if ! "$VENV/bin/python" - <<'PY'
from importlib.metadata import version
assert version("cocotb")=="2.1.0"
assert version("pytest")=="8.4.2"
import cocotb
import cocotb_tools
PY
then
    fail "Python version verification" "Installed versions unexpected"
fi
say PASS "Local cocotb dependencies" "Pinned cocotb 2.1.0 and pytest 8.4.2; isolated venv"
if ! (cd "$WORK/template/test" &&
    export PATH="$VENV/bin:$PATH" &&
    timeout 180s make clean &&
    timeout 180s make) >"$WORK/cocotb.log" 2>&1; then
    fail "Official-template RTL cocotb" "Simulation/build failed; inspect cocotb.log"
fi
say PASS "Official-template cocotb runner" "Official test/Makefile finished with iverilog"
if ! (cd "$WORK/template/test" &&
    "$VENV/bin/python" -m cocotb_tools.check_results results.xml) \
    >"$WORK/results-check.log" 2>&1; then
    fail "Cocotb results.xml" "Test failures recorded or results missing"
fi
say PASS "Cocotb results.xml" "Official cocotb_tools.check_results confirmed test pass"
if ! python3 - "$WORK/template/test/results.xml" >>"$LOG" 2>&1 <<'PY'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
path=Path(sys.argv[1])
assert path.is_file()
root=ET.parse(path).getroot()
tests=root.findall(".//testcase")
assert tests, "No testcases in results.xml"
failed=[t for t in tests if t.find("failure") is not None or t.find("error") is not None]
assert not failed, f"cocotb XML recorded {len(failed)} failures"
print("PASS | Cocotb XML summary |",len(tests),"testcase(s), zero failures")
PY
then
    fail "XML verification" "Unable to parse generated test results"
fi
verify_gds "$GDS2C" "$SHA2C"
verify_gds "$GDS2F" "$SHA2F"
say PASS "Original UART layouts" "Both independent GDSII SHA256 values unchanged"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    say PASS "User Git working tree" "Clean; original RTL untouched"
else
    say WARN "User Git working tree" "Unexpected uncommitted changes detected; no cleanup performed"
fi
say INFO "Local RTL-only scope" "No provider GDS action, gate-level signoff, tile selection, purchase or shuttle submission"
say INFO "Detailed cocotb simulation log" "$WORK/cocotb.log"
say INFO "Results XML" "$WORK/template/test/results.xml"
say INFO "Full G: summary" "$LOG"
echo "===== END ASIC STAGE 3C ====="

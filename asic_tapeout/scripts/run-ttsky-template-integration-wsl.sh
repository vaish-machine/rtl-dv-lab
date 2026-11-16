#!/usr/bin/env bash
# ASIC Stage 3B: local pinned official TT SKY130 template dry-run.
# No GitHub repo creation, action trigger, PDK change, payment or submission.
# Creates a unique G:-backed WSL ext4 workspace with official template copy.
set -Eeuo pipefail
ROOT="/mnt/g/C-Drive-Backup-PreReset"
TEMP="$ROOT/Temp"
REPO="/home/vaish/projects/rtl-dv-lab"
BASE="/home/vaish/DevTools/LibreLane/ttsky_official_template_dryrun"
TEMPLATE_URL="https://github.com/TinyTapeout/ttsky-verilog-template.git"
TEMPLATE_SHA="a42e6662fab316e93b4e26399e21d41664a460b7"
GDS2C="/home/vaish/DevTools/LibreLane/uart_sky130_explore/uart-core-alMhK5du/runs/explore-20261116-061728/final/gds/uart_core.gds"
GDS2F="/home/vaish/DevTools/LibreLane/uart_sky130_constrained/uart-core-sdc-bC4s4a9x/runs/sdc-explore-20261116-074159/final/gds/uart_core.gds"
SHA2C="3ab1c89ee9de3d087ca261f7835aacbd8f21afef79d254e72ec9c2bb1d46dbf3"
SHA2F="d63d047d083548a649710ac194fcd09c110ad3f20bff65a6752d89da5e9dd7af"
WORK=""
LOG=""
echo "===== ASIC STAGE 3B: OFFICIAL TTSKY TEMPLATE LOCAL DRY RUN ====="
if [[ ! -d "$TEMP" ]]; then
    echo "FAIL | G: Temp not found"
    exit 1
fi
LOG="$TEMP/ASIC-Stage3B-TTSKY-Template-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
say() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
fail() {
    say FAIL "$1" "$2"
    if [[ -n "$WORK" ]]; then
        for f in "$WORK/clone.log" "$WORK/compile.log" "$WORK/yosys.log" "$WORK/cocotb.log"; do
            if [[ -s "$f" ]]; then
                echo "INFO | Diagnostic tail | $f"
                tail -n 11 "$f" || true
            fi
        done
        say INFO "Preserved workspace" "$WORK"
    fi
    say INFO "Detailed G: audit log" "$LOG"
    exit 1
}
verify_gds() {
    local path="$1" expected="$2" actual
    [[ -f "$path" && ! -L "$path" ]] ||
        fail "GDSII preservation" "Missing or symlink: $path"
    actual="$(sha256sum "$path" | awk '{print $1}')"
    [[ "$actual" == "$expected" ]] ||
        fail "GDSII preservation" "Unexpected SHA256 $actual"
}
[[ "$(id -un)" == "vaish" && "$(id -u)" != "0" ]] ||
    fail "Ubuntu identity" "Expected non-root user vaish"
for bin in git iverilog yosys python3 mktemp sha256sum df awk grep make; do
    command -v "$bin" >/dev/null 2>&1 ||
        fail "Prerequisite" "Missing $bin"
done
[[ -d "$REPO/.git" ]] ||
    fail "User repo" "Expected local rtl-dv-lab checkout missing"
[[ "$(git -C "$REPO" branch --show-current)" == main ]] ||
    fail "User repo" "Expected main"
[[ "$(git -C "$REPO" remote get-url origin)" == "https://github.com/vaish-machine/rtl-dv-lab.git" ]] ||
    fail "User repo" "Unexpected origin"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] ||
    fail "User repo" "Local edits detected; no fetch/merge"
say PASS "User repo preflight" "Clean main with expected origin"
git -C "$REPO" fetch origin main >> "$LOG" 2>&1 ||
    fail "Git fetch" "Failed; no merge"
git -C "$REPO" merge-base --is-ancestor HEAD origin/main ||
    fail "Git preflight" "Diverged main; no merge"
git -C "$REPO" merge --ff-only origin/main >> "$LOG" 2>&1 ||
    fail "Git fast-forward" "Unable to fast-forward"
REV="$(git -C "$REPO" rev-parse HEAD)"
say PASS "Source Git fast-forward" "$REV"
verify_gds "$GDS2C" "$SHA2C"
verify_gds "$GDS2F" "$SHA2F"
say PASS "Original Stage 2C/2F GDSII" "Both exact SHA256 values intact"
AVAILABLE="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
[[ "$AVAILABLE" =~ ^[0-9]+$ && "$AVAILABLE" -gt 5242880 ]] ||
    fail "G: free space" "At least 5 GiB required"
say PASS "G: available" "$((AVAILABLE / 1048576)) GiB"
SRC="$REPO/asic_tapeout"
TT="$SRC/shuttle/ttsky_candidate"
for path in \
    "$SRC/rtl/uart_tx.sv" "$SRC/rtl/uart_rx.sv" "$SRC/rtl/uart_core.sv" \
    "$TT/src/tt_um_vaish_uart.v" "$TT/info.stage3b.yaml" "$TT/test/test.py"; do
    [[ -f "$path" && ! -L "$path" ]] ||
        fail "Candidate files" "Missing or symlink: $path"
done
mkdir -p "$BASE"
WORK="$(mktemp -d "$BASE/ttsky-XXXXXXXX")"
export TMPDIR="$WORK"
say INFO "G:-backed isolated workspace" "$WORK"
git clone -q "$TEMPLATE_URL" "$WORK/template" > "$WORK/clone.log" 2>&1 ||
    fail "Official template clone" "Clone failed"
git -C "$WORK/template" checkout --detach --quiet "$TEMPLATE_SHA" >> "$WORK/clone.log" 2>&1 ||
    fail "Official template pin" "Cannot check out exact official template revision"
[[ "$(git -C "$WORK/template" rev-parse HEAD)" == "$TEMPLATE_SHA" ]] ||
    fail "Official template SHA" "Unexpected template commit"
say PASS "Official SKY template pin" "$TEMPLATE_SHA"
for file in "$WORK/template/src/project.v" "$WORK/template/info.yaml" \
    "$WORK/template/test/Makefile" "$WORK/template/test/tb.v" \
    "$WORK/template/test/requirements.txt" \
    "$WORK/template/.github/workflows/gds.yaml"; do
    [[ -f "$file" ]] ||
        fail "Official template structure" "Expected official file missing: $file"
done
say PASS "Official template structure" "src, info.yaml, test, GDS workflow present"
cp "$SRC/rtl/uart_tx.sv" "$SRC/rtl/uart_rx.sv" \
   "$SRC/rtl/uart_core.sv" "$TT/src/tt_um_vaish_uart.v" "$WORK/template/src/"
cp "$TT/info.stage3b.yaml" "$WORK/template/info.yaml"
cp "$TT/test/test.py" "$WORK/template/test/test.py"
# The earlier heredoc had a dangling || failure handler placed ahead of
# the Python body; Bash fed the failure-handler line to Python instead of
# executing the actual patch. The corrected if/then surrounds the full body.
# Change only the unique official placeholder name and source list in the
# LOCAL TEMPORARY TEMPLATE COPY. Preserve the official Makefile structure.
if ! python3 - "$WORK/template" >"$WORK/template-check.log" 2>&1 <<'PY'
from pathlib import Path
import re
import sys

base=Path(sys.argv[1])
test=base/"test"
tb=test/"tb.v"
text=tb.read_text(encoding="utf-8")
assert text.count("tt_um_example")==2, "Pinned official tb.v changed: expected one comment and one instantiation"
tb.write_text(text.replace("tt_um_example","tt_um_vaish_uart"),encoding="utf-8")
mk=test/"Makefile"
make=mk.read_text(encoding="utf-8")
assert make.count("PROJECT_SOURCES = project.v")==1, "Pinned Makefile changed"
files="tt_um_vaish_uart.v uart_core.sv uart_tx.sv uart_rx.sv"
make=make.replace("PROJECT_SOURCES = project.v", "PROJECT_SOURCES = "+files)
mk.write_text(make,encoding="utf-8")
placeholder=base/"src/project.v"
assert placeholder.is_file()
placeholder.unlink()  # only in brand-new isolated template copy
yaml=(base/"info.yaml").read_text(encoding="utf-8")
assert 'top_module: "tt_um_vaish_uart"' in yaml
assert 'tiles: "1x1"' in yaml
assert "PLACEHOLDER" in yaml
assert "yaml_version: 6" in yaml
sources=re.findall(r'(?m)^    - "([^"]+)"\s*$',yaml)
assert set(sources)==set(files.split()) and len(sources)==4, sources
for file in sources:
    assert (base/"src"/file).is_file(), file
assert "PROJECT_SOURCES = "+files in make
assert "tt_um_vaish_uart user_project" in tb
assert "tt_um_example" not in tb
print("PASS | Template overlay consistency | official TB + source list + YAML v6")
PY
then
    fail "Official template overlay" "Metadata, tb.v or Makefile patch/validation failed"
fi
if ! grep -Fq "PASS | Template overlay consistency" "$WORK/template-check.log"; then
    fail "Official template overlay" "Python patch did not confirm completing"
fi
if grep -Eq 'tt_um_example[[:space:]]+user_project' "$WORK/template/test/tb.v"; then
    fail "Official testbench top" "Old official placeholder remains after overlay"
fi
if ! grep -Eq 'tt_um_vaish_uart[[:space:]]+user_project' "$WORK/template/test/tb.v"; then
    fail "Official testbench top" "Expected candidate top missing after overlay"
fi
say PASS "Official template overlay" "Python executed; official tb.v top, metadata, Makefile and sources verified"
say REVIEW "Tile shape" "1x1 is UNVERIFIED PLACEHOLDER, not a proved fit or reserved area"
say INFO "Clock" "10 MHz is provisional educational metadata, not shuttle contract"
# Check default SKY workflows have not been edited.
if [[ -n "$(git -C "$WORK/template" diff -- .github/workflows)" ]]; then
    fail "Official workflows" "Template GitHub Actions changed unexpectedly"
fi
say PASS "Provider workflow preservation" "Official GDS/CI files unmodified in workspace"
( cd "$WORK/template"; sha256sum src/* test/test.py info.yaml ) >"$WORK/staged-source-sha256.txt"

# Compiles the OFFICIAL test/tb.v with the candidate top and all sources.
iverilog -g2012 -s tb -o "$WORK/template-top.vvp" \
    "$WORK/template/test/tb.v" \
    "$WORK/template/src/uart_tx.sv" "$WORK/template/src/uart_rx.sv" \
    "$WORK/template/src/uart_core.sv" "$WORK/template/src/tt_um_vaish_uart.v" \
    >"$WORK/compile.log" 2>&1 ||
    fail "Official template TB compile" "Icarus compilation failed"
say PASS "Official template TB compile" "UART sources and provider test/tb.v compiled"
yosys -Q -T -p \
    "read_verilog -sv $WORK/template/src/uart_tx.sv $WORK/template/src/uart_rx.sv $WORK/template/src/uart_core.sv $WORK/template/src/tt_um_vaish_uart.v; hierarchy -check -top tt_um_vaish_uart; proc; opt; check -assert" \
    >"$WORK/yosys.log" 2>&1 ||
    fail "Candidate structural Yosys" "RTL hierarchy check failed"
say PASS "Yosys candidate hierarchy" "Expected TT top hierarchy and structural assertions"

# Run the official Makefile/cocotb flow only when already available. Do NOT
# install packages, create pip caches, run provider CI or claim a false PASS.
if command -v cocotb-config >/dev/null 2>&1 &&
   python3 -c 'import cocotb, cocotb_tools' >/dev/null 2>&1; then
    if ! (cd "$WORK/template/test" && make clean && make) \
        >"$WORK/cocotb.log" 2>&1; then
        fail "Local official Makefile cocotb" "Simulation failed; see G:-backed cocotb.log"
    fi
    if ! (cd "$WORK/template/test" &&
          python3 -m cocotb_tools.check_results results.xml) \
        >>"$WORK/cocotb.log" 2>&1; then
        fail "Local cocotb results" "results.xml check failed"
    fi
    say PASS "Local template cocotb" "Official Makefile with UART test.py and results.xml checker"
else
    say SKIP "Local template cocotb" "Not installed; no auto-install or false PASS"
fi
verify_gds "$GDS2C" "$SHA2C"
verify_gds "$GDS2F" "$SHA2F"
say PASS "Preserved UART GDSII" "Stage 2C and 2F unchanged after template dry-run"
if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then
    say PASS "User Git working tree" "Clean; original RTL remains untouched"
else
    say WARN "User Git working tree" "Unexpected local changes; no cleanup attempted"
fi
say INFO "Staged official template" "$WORK/template"
say INFO "G: log" "$LOG"
say INFO "Approval boundaries" "No provider GDS, tile-fit approval, slot purchase or shuttle submission"
echo "===== END ASIC STAGE 3B ====="

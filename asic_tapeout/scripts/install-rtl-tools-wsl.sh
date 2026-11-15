#!/usr/bin/env bash
# ASIC Stage 0I: Ubuntu 24.04 RTL tool baseline and standalone smoke tests.
# Packages are installed inside existing G:-backed Ubuntu WSL ext4.vhdx.
# Diagnostics and smoke-test files are saved under G:\C-Drive-Backup-PreReset\Temp.
# Does not modify source repo, install PDK/OpenROAD, or perform a tapeout.
set -Eeuo pipefail

ROOT="/mnt/g/C-Drive-Backup-PreReset"
LOG_DIR="$ROOT/Temp"
REPO="$HOME/projects/rtl-dv-lab"
echo "===== ASIC STAGE 0I: RTL TOOLS AND SMOKE TESTS ====="

if [[ ! -d "$LOG_DIR" ]]; then
  echo "FAIL | G: Temp not mounted; no installation attempted"
  exit 1
fi
LOG="$LOG_DIR/ASIC-Stage0I-RTL-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
fail() {
  echo "FAIL | $1"
  echo "FAIL | $1" >> "$LOG"
  echo "INFO | Detailed log: $LOG"
  exit 1
}
report() {
  printf '%s | %s | %s\n' "$1" "$2" "$3"
  printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}

[[ "$(id -u)" != "0" && "$(id -un)" == "vaish" ]] || fail "Run as normal Ubuntu user vaish"
source /etc/os-release
[[ "$ID" == "ubuntu" && "$VERSION_ID" == "24.04" ]] || fail "Requires Ubuntu 24.04"
[[ -d "$REPO/.git" && -f "$REPO/asic_tapeout/README.md" ]] || fail "Existing G:-backed rtl-dv-lab clone not found"
report PASS "Ubuntu" "$PRETTY_NAME"
report PASS "User" "$(id -un), UID $(id -u)"
report PASS "Local repository" "$REPO"
report INFO "Log location" "$LOG"

if ! sudo -v; then fail "sudo authentication failed; no packages installed"; fi
report PASS "Sudo" "Authorized; password not saved"

report INFO "APT update" "Output redirected to G: log"
if ! sudo env DEBIAN_FRONTEND=noninteractive apt-get update >> "$LOG" 2>&1; then
  fail "apt-get update failed; inspect G: log"
fi
report PASS "APT update" "Completed"

PACKAGES="yosys verilator iverilog build-essential python3 python3-venv python3-pip tcl z3"
for pkg in $PACKAGES; do
  candidate="$(apt-cache policy "$pkg" | sed -n 's/^[[:space:]]*Candidate: //p')"
  if [[ -z "$candidate" || "$candidate" == "(none)" ]]; then
    fail "APT package unavailable: $pkg (check Ubuntu universe/repositories)"
  fi
done
report PASS "APT candidates" "Core RTL packages available"

report INFO "Package installation" "Yosys, Verilator, Icarus, build tools, Python, Tcl, Z3"
if ! sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $PACKAGES >> "$LOG" 2>&1; then
  fail "APT install failed; inspect G: log before retry"
fi
report PASS "APT installation" "Completed"

for binary in yosys verilator iverilog vvp gcc g++ make python3 z3; do
  command -v "$binary" >/dev/null 2>&1 || fail "Required executable missing: $binary"
done
report PASS "Yosys" "$(yosys -V)"
report PASS "Verilator" "$(verilator --version)"
report PASS "Icarus Verilog" "$(iverilog -V 2>&1 | sed -n '1p')"
report PASS "Compiler" "$(gcc --version | sed -n '1p')"
report PASS "Python" "$(python3 --version)"
report PASS "Z3" "$(z3 --version)"

# Test fixtures are created outside of the local Git repository.
WORK="$(mktemp -d "$LOG_DIR/ASIC-Stage0I-Smoke.XXXXXXXX")"
report INFO "Smoke-test workspace" "$WORK"
cat > "$WORK/counter.sv" <<'RTL'
module counter (
  input  logic       clk,
  input  logic       rst_n,
  output logic [3:0] count
);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      count <= 4'd0;
    else
      count <= count + 4'd1;
  end
endmodule
RTL
cat > "$WORK/tb.sv" <<'TB'
module tb;
  logic clk = 1'b0;
  logic rst_n = 1'b0;
  wire [3:0] count;
  counter dut (.clk(clk), .rst_n(rst_n), .count(count));
  initial begin
    #1 clk = 1'b1;
    #1 clk = 1'b0; rst_n = 1'b1;
    #1 clk = 1'b1;
    #1;
    if (count !== 4'd1) $fatal(1, "counter mismatch");
    $display("ASIC_STAGE0I_SIM_PASS");
    $finish;
  end
endmodule
TB

if ! iverilog -g2012 -s tb -o "$WORK/tb.vvp" "$WORK/counter.sv" "$WORK/tb.sv" >> "$LOG" 2>&1; then
  fail "Icarus compile smoke test failed"
fi
if ! vvp "$WORK/tb.vvp" > "$WORK/iverilog-run.log" 2>&1; then
  cat "$WORK/iverilog-run.log" >> "$LOG"
  fail "Icarus simulation failed"
fi
if ! grep -q '^ASIC_STAGE0I_SIM_PASS$' "$WORK/iverilog-run.log"; then
  cat "$WORK/iverilog-run.log" >> "$LOG"
  fail "Icarus testbench did not report PASS"
fi
report PASS "Icarus RTL simulation" "Counter checked with self-checking testbench"

if ! verilator --lint-only --sv --top-module counter "$WORK/counter.sv" >> "$LOG" 2>&1; then
  fail "Verilator lint smoke test failed"
fi
report PASS "Verilator lint" "Counter RTL accepted"

if ! yosys -Q -T -p "read_verilog -sv $WORK/counter.sv; synth -top counter; stat" >> "$LOG" 2>&1; then
  fail "Yosys synthesis smoke test failed"
fi
report PASS "Yosys synthesis" "Counter RTL synthesized"

if [[ -n "$(git -C "$REPO" status --porcelain)" ]]; then
  report WARN "Repository working tree" "Has changes; no cleanup performed"
else
  report PASS "Repository working tree" "Clean; smoke tests did not modify source"
fi
report INFO "Tools storage" "Ubuntu native ext4 filesystem (G:-backed VHDX)"
report INFO "Physical design" "OpenROAD/LibreLane/PDK not installed by Stage 0I"
report INFO "Detailed log" "$LOG"
echo "===== END ASIC STAGE 0I ====="

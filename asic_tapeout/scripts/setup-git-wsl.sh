#!/usr/bin/env bash
# ASIC Stage 0H: install Linux Git and clone the existing public RTL/DV repo.
# Ubuntu ext4.vhdx is on G:, so Linux packages and ~/projects live on G:.
# Does not delete or overwrite prior checkouts or install Windows/EDA tools.
set -Eeuo pipefail
ROOT="/mnt/g/C-Drive-Backup-PreReset"
LOG_DIR="$ROOT/Temp"
REPO_URL="https://github.com/vaish-machine/rtl-dv-lab.git"
TARGET="$HOME/projects/rtl-dv-lab"
LOG="$LOG_DIR/ASIC-Stage0H-Git-$(date +%Y%m%d-%H%M%S).log"
echo "===== ASIC STAGE 0H: GIT AND WSL SOURCE SETUP ====="
fail() {
  printf 'FAIL | %s\n' "$1"
  if [[ -f "$LOG" ]]; then printf 'FAIL | %s\n' "$1" >> "$LOG"; fi
  exit 1
}
report() {
  printf '%s | %s | %s\n' "$1" "$2" "$3"
  printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
[[ -d "$LOG_DIR" ]] || fail "G: Temp not mounted; no packages installed"
touch "$LOG" || fail "Cannot write G: log; no packages installed"
[[ "$(id -un)" == "vaish" && "$(id -u)" != "0" ]] || fail "Run as non-root Ubuntu user vaish"
source /etc/os-release
[[ "$ID" == "ubuntu" && "$VERSION_ID" == "24.04" ]] || fail "Expected Ubuntu 24.04"
report PASS "Ubuntu" "$PRETTY_NAME"
report PASS "User" "$(id -un), UID $(id -u)"
report INFO "Log" "$LOG"
if ! sudo -v; then fail "sudo authentication failed; no package installation attempted"; fi
report PASS "Sudo" "Authentication accepted; password not saved"
report INFO "APT update" "Output redirected to G: log"
if ! sudo env DEBIAN_FRONTEND=noninteractive apt-get update >> "$LOG" 2>&1; then
  fail "apt-get update failed; inspect G: log"
fi
report PASS "APT update" "Completed"
report INFO "Git installation" "Installing git and ca-certificates"
if ! sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends git ca-certificates >> "$LOG" 2>&1; then
  fail "apt-get install failed; inspect G: log"
fi
command -v git >/dev/null 2>&1 || fail "git binary not found after installation"
report PASS "Linux Git" "$(git --version)"
if [[ -e "$TARGET" || -L "$TARGET" ]]; then
  if [[ -d "$TARGET/.git" ]]; then
    report WARN "Existing checkout" "$TARGET exists; not overwritten or updated"
    actual_remote="$(git -C "$TARGET" remote get-url origin 2>/dev/null || true)"
    report INFO "Existing remote" "$actual_remote"
    if [[ "$actual_remote" != "$REPO_URL" ]]; then
      fail "Existing checkout has unexpected remote; review manually"
    fi
  else
    fail "Target already exists and is not a valid checkout; refusing overwrite"
  fi
else
  mkdir -p "$HOME/projects"
  report INFO "Git clone" "Cloning public rtl-dv-lab under Linux home on G: virtual disk"
  if ! git clone --branch main "$REPO_URL" "$TARGET" >> "$LOG" 2>&1; then
    fail "git clone failed; check log and partial destination before retrying"
  fi
  report PASS "Git clone" "Completed"
fi
current_commit="$(git -C "$TARGET" rev-parse --short=12 HEAD 2>/dev/null || true)"
[[ "$current_commit" =~ ^[0-9a-f]{12}$ ]] || fail "Cannot verify local commit"
report PASS "Local HEAD" "$current_commit"
branch="$(git -C "$TARGET" branch --show-current)"
report INFO "Branch" "$branch"
[[ "$branch" == "main" ]] || fail "Expected main branch; no changes made"
[[ -f "$TARGET/asic_tapeout/README.md" && -f "$TARGET/mux10_uvm_starter/README.md" ]] || fail "Project files not found after clone"
report PASS "Both project tracks" "ASIC planning and existing mux UVM source present"
if [[ -z "$(git -C "$TARGET" status --porcelain)" ]]; then
  report PASS "Working tree" "Clean"
else
  report WARN "Working tree" "Has local modifications; no cleanup performed"
fi
report INFO "Linux project folder" "$TARGET (inside G:-backed WSL virtual disk)"
report INFO "Windows Git" "Not installed; optional for Linux ASIC workflow"
report INFO "ASIC tools" "Not installed by Stage 0H"
echo "===== END ASIC STAGE 0H ====="

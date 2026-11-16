#!/usr/bin/env bash
# ASIC Stage 2B: verify and copy official LibreLane devshell to native Ubuntu ext4
# (backed by G:\ WSL VHDX), then run its official bundled smoke test.
# No RTL modifications, root shell, weakening AppArmor or physical UART run.
set -Eeuo pipefail
ROOT="/mnt/g/C-Drive-Backup-PreReset"
LOGDIR="$ROOT/Temp"
SRC="$ROOT/Installers/LibreLane/LibreLane-3.0.17-librelane-devshell-x86_64.AppImage"
DESTDIR="$HOME/DevTools/LibreLane/3.0.17"
DEST="$DESTDIR/librelane-devshell-x86_64.AppImage"
PART="$DEST.part"
SIZE=1398049312
SHA="c8ef5ae26b1fc53dd1dd30fe2f1a1da6ab0fdf471dd5a94c2b85d2b3db36833c"
echo "===== ASIC STAGE 2B: LIBRELANE SETUP AND SMOKE TEST ====="
if [[ ! -d "$LOGDIR" ]]; then
    echo "FAIL | G: Temp not mounted; no installation attempted"
    exit 1
fi
LOG="$LOGDIR/ASIC-Stage2B-LibreLane-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG"
report() {
    printf '%s | %s | %s\n' "$1" "$2" "$3"
    printf '%s | %s | %s\n' "$1" "$2" "$3" >> "$LOG"
}
fail() {
    report FAIL "$1" "$2"
    echo "===== COMPACT ERROR DIAGNOSTICS ====="
    grep -Ei 'fatal|error:|traceback|failed|cannot write uid_map|operation not permitted|fuse|AppArmor|permission denied|No such file' "$LOG" | tail -n 16 || true
    echo "===== END ERROR DIAGNOSTICS ====="
    echo "INFO | Detailed log: $LOG"
    exit 1
}
[[ "$(id -un)" == vaish && "$(id -u)" != 0 ]] ||
    fail "Linux user" "Expected non-root Ubuntu user vaish"
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] ||
    fail "OS" "Expected Ubuntu 24.04"
[[ "$(uname -m)" == x86_64 ]] || fail "Architecture" "Expected x86_64"
for tool in sha256sum stat cp chmod mv df awk grep timeout sysctl mktemp; do
    command -v "$tool" >/dev/null 2>&1 ||
        fail "Prerequisites" "Missing executable: $tool"
done
report PASS "Ubuntu" "$PRETTY_NAME, x86_64"
[[ -f "$SRC" && ! -L "$SRC" ]] ||
    fail "Official AppImage" "File missing at $SRC"
[[ "$(stat -c %s "$SRC")" == "$SIZE" ]] ||
    fail "Publisher size" "Expected $SIZE bytes"
report PASS "Publisher size" "$SIZE bytes"
SRC_SHA="$(sha256sum "$SRC" | awk '{print $1}')"
[[ "$SRC_SHA" == "$SHA" ]] ||
    fail "Publisher SHA256" "Digest mismatch; no execution attempted"
report PASS "Publisher SHA256" "$SRC_SHA"

# The WSL ext4.vhdx grows on G:, so also verify host drive free space.
G_FREE_KB="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
[[ "$G_FREE_KB" =~ ^[0-9]+$ ]] ||
    fail "G: space" "Cannot read free space"
[[ "$G_FREE_KB" -ge 12582912 ]] ||
    fail "G: space" "Less than 12 GiB free; no copy attempted"
report PASS "G: available space" "$((G_FREE_KB / 1048576)) GiB free"
[[ ! -L "$DESTDIR" ]] ||
    fail "Linux destination" "Symlink found; refusing to write"
mkdir -p "$DESTDIR" "$HOME/DevTools/LibreLane/tmp" \
    "$HOME/DevTools/LibreLane/pdks" "$HOME/.cache"
[[ ! -e "$PART" && ! -L "$PART" ]] ||
    fail "Partial destination" "Partial copy exists; preserved for review"
if [[ -e "$DEST" || -L "$DEST" ]]; then
    [[ -f "$DEST" && ! -L "$DEST" ]] ||
        fail "Existing destination" "Not a regular file; stopped"
    report INFO "Linux AppImage" "Existing file; verifying without overwriting"
else
    report INFO "Linux copy" "$DEST (G:-backed Ubuntu native ext4)"
    if ! cp "$SRC" "$PART" >> "$LOG" 2>&1; then
        fail "Linux copy" "Failed; partial copy preserved"
    fi
    [[ "$(stat -c %s "$PART")" == "$SIZE" ]] ||
        fail "Staged size" "Mismatch; partial copy preserved"
    [[ "$(sha256sum "$PART" | awk '{print $1}')" == "$SHA" ]] ||
        fail "Staged SHA256" "Mismatch; partial copy preserved"
    chmod 0755 "$PART"
    mv -n "$PART" "$DEST"
    report PASS "Linux native copy" "Verified and placed on G:-backed ext4"
fi
[[ "$(stat -c %s "$DEST")" == "$SIZE" ]] ||
    fail "Installed size" "Mismatch; refused execution"
[[ "$(sha256sum "$DEST" | awk '{print $1}')" == "$SHA" ]] ||
    fail "Installed SHA256" "Mismatch; refused execution"
chmod 0755 "$DEST"
report PASS "Installed SHA256" "$SHA"
report PASS "Installed AppImage" "$DEST"

# LibreLane official WSL docs recommend uidmap to resolve uid_map failures.
# Install only this Ubuntu package if helpers are missing; do not alter sysctls.
if ! command -v newuidmap >/dev/null 2>&1 ||
   ! command -v newgidmap >/dev/null 2>&1; then
    report INFO "uidmap helpers" "Not found; installing Ubuntu uidmap package"
    if ! sudo -v >> "$LOG" 2>&1; then
        fail "uidmap" "sudo authorization failed"
    fi
    if ! sudo env DEBIAN_FRONTEND=noninteractive apt-get update >> "$LOG" 2>&1 ||
       ! sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends uidmap >> "$LOG" 2>&1; then
        fail "uidmap" "Ubuntu APT installation failed; inspect G: log"
    fi
fi
command -v newuidmap >/dev/null 2>&1 ||
    fail "uidmap" "newuidmap missing"
command -v newgidmap >/dev/null 2>&1 ||
    fail "uidmap" "newgidmap missing"
report PASS "uidmap helpers" "newuidmap and newgidmap present"
APPARMOR="$(sysctl -n kernel.apparmor_restrict_unprivileged_userns 2>/dev/null || true)"
report INFO "AppArmor namespace setting" "$APPARMOR (not modified)"

export TMPDIR="$HOME/DevTools/LibreLane/tmp"
export XDG_CACHE_HOME="$HOME/.cache"
export PDK_ROOT="$HOME/DevTools/LibreLane/pdks"
export PYTHONIOENCODING=utf-8
WORK="$(mktemp -d "$TMPDIR/stage2b-smoke.XXXXXXXX")"
cd "$WORK"
report INFO "Working directory" "$WORK"
report INFO "PDK directory" "$PDK_ROOT"
report INFO "Version check" "Invoking official devshell with librelane --version"
if ! timeout 300 "$DEST" librelane --version > "$WORK/version.log" 2>&1; then
    cat "$WORK/version.log" >> "$LOG"
    fail "LibreLane launch" "Version check failed; no smoke test attempted"
fi
cat "$WORK/version.log" >> "$LOG"
grep -Fq "3.0.17" "$WORK/version.log" ||
    fail "LibreLane version" "Version mismatch; no smoke attempted"
report PASS "LibreLane version" "3.0.17"
report INFO "Official smoke test" "Running bundled example; PDK/cache/temp stay on G:"
if ! timeout 3600 "$DEST" librelane --smoke-test > "$WORK/smoke.log" 2>&1; then
    cat "$WORK/smoke.log" >> "$LOG"
    fail "LibreLane smoke" "Failed or exceeded timeout; details saved"
fi
cat "$WORK/smoke.log" >> "$LOG"
grep -Fq "Smoke test passed." "$WORK/smoke.log" ||
    fail "Smoke success marker" "Missing despite exit code 0"
report PASS "LibreLane official smoke" "Smoke test passed (bundled example, NOT UART)"
report INFO "Source repository" "No RTL or Git edits"
report INFO "Security policy" "No AppArmor/sysctl changes"
report INFO "Detailed log" "$LOG"
echo "===== END ASIC STAGE 2B ====="

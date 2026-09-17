#!/bin/sh
# plan-script-path.sh — which copy of a `plan` script should a hook run?
#
#   sh plan-script-path.sh <name> <cwd> [hooks-dir] [seal-root]
#
# **EXECUTED, never sourced.** Sourcing put this file's failure modes inside the hook's own
# process — a stray `exit` ended the hook before its gate ran, a syntax error left a half-defined
# function behind. Each hook computes its deployed path first, runs this, and uses the answer only
# if it comes back a real file, so nothing here reaches the hook except one line of stdout.
#
# 🛑 **The environment is not trusted, and this is the whole security model.**
# Every input is an ARGUMENT. Earlier versions read `PLAN_HOOK_DIR` and `PLAN_SEAL_ROOT` from the
# environment "for testability", and hooks inherit the session's environment: a session started
# with `PLAN_SEAL_ROOT=/tmp/evil` made all four hooks execute `/tmp/evil/<hex>/<name>`. A
# testability seam became arbitrary code execution — the second time that exact mistake shipped
# here in one day. Tests pass the overrides as arguments; production passes none.
#
# The chain of trust, in order:
#   1. `hooks-dir` — argument, else this file's own physical directory. Gives the DEPLOYED copy,
#      which is the answer whenever anything below is unsatisfied.
#   2. `plan-builder-root` beside it — one absolute path, the ONE repository that may supply
#      scripts. Named, never detected: a first version asked "does this session's repo look like
#      the builder?", which let any checkout supply code.
#   3. `cwd` must be that path or inside it, resolved physically.
#   4. The builder's LIVE tree is still never executed — only a sealed snapshot (see
#      `seal_plan_scripts.sh`). Editing and publishing-to-the-hooks are separate acts.
#
# **What this does NOT defend against.** The builder is a TRUST ROOT, not a sandbox: whoever can
# write its sealed snapshots, or the `plan-builder-root` file, chooses what these hooks execute.
# The rule stops an unrelated repository and a hostile environment; it does not make the builder
# safe. `PSK-OL-09` carries this.
#
# POSIX sh, no bashisms.

plan_script() {
    _ps_name="$1"
    _ps_cwd="${2:-$PWD}"
    _ps_here="${3:-}"
    _ps_seal_root="${4:-}"

    # A bare filename, never a path: `../../../x.py` composed a traversing path out of both roots.
    case "$_ps_name" in
        ""|*/*|.|..) echo "" ; return 1 ;;
    esac

    if [ -z "$_ps_here" ]; then
        _ps_here="$(cd -P "$(dirname "$0")" 2>/dev/null && pwd)" || _ps_here=""
    fi
    [ -n "$_ps_here" ] || { echo "" ; return 1; }
    _ps_deployed="${_ps_here%/hooks}/skills/plan/scripts/$_ps_name"

    _ps_conf="$_ps_here/plan-builder-root"
    [ -r "$_ps_conf" ] || { echo "$_ps_deployed"; return 0; }
    [ -h "$_ps_conf" ] && { echo "$_ps_deployed"; return 0; }
    _ps_builder="$(sed -n '1s/[[:space:]]*$//p' "$_ps_conf" 2>/dev/null)"
    # ABSOLUTE ONLY — a relative value is resolved against the SESSION'S cwd, so `.` made whatever
    # repository the session was in the builder. `/` is the whole filesystem and is not a builder.
    case "$_ps_builder" in
        /) echo "$_ps_deployed"; return 0 ;;
        /*) ;;
        *) echo "$_ps_deployed"; return 0 ;;
    esac
    _ps_builder="$(cd -P "$_ps_builder" 2>/dev/null && pwd)" || _ps_builder=""
    [ -n "$_ps_builder" ] || { echo "$_ps_deployed"; return 0; }

    _ps_cwd="$(cd -P "$_ps_cwd" 2>/dev/null && pwd)" || _ps_cwd=""
    [ -n "$_ps_cwd" ] || { echo "$_ps_deployed"; return 0; }
    case "$_ps_cwd" in
        "$_ps_builder"|"$_ps_builder"/*) ;;
        *) echo "$_ps_deployed"; return 0 ;;
    esac

    # The seal root sits beside the configuration that names the builder, so the same person who
    # decides WHO may supply code decides WHERE from. Never from the environment.
    [ -n "$_ps_seal_root" ] || _ps_seal_root="$_ps_here/plan-seal"
    [ -h "$_ps_seal_root" ] && { echo "$_ps_deployed"; return 0; }
    _ps_seal_root="$(cd -P "$_ps_seal_root" 2>/dev/null && pwd)" || _ps_seal_root=""
    [ -n "$_ps_seal_root" ] || { echo "$_ps_deployed"; return 0; }

    _ps_ptr="$_ps_seal_root/CURRENT"
    [ -f "$_ps_ptr" ] || { echo "$_ps_deployed"; return 0; }
    [ -h "$_ps_ptr" ] && { echo "$_ps_deployed"; return 0; }
    # The WHOLE file must be one hash line. Reading only the first line accepted a valid line
    # followed by anything at all, which is not what "a hash and nothing else" means.
    # Exactly 65 bytes: 64 hex plus one newline. A line count is not enough — `/bin/sh` silently
    # DROPS NUL bytes from command substitution, so a pointer of `deadbeef<NUL>` was one line,
    # read back as `deadbeef`, and passed the hex check. Byte count sees what the shell cannot.
    [ "$(wc -c < "$_ps_ptr" 2>/dev/null | tr -d ' ')" = "65" ] || { echo "$_ps_deployed"; return 0; }
    [ "$(wc -l < "$_ps_ptr" 2>/dev/null | tr -d ' ')" = "1" ] || { echo "$_ps_deployed"; return 0; }
    # The 65th byte must BE the newline. `32 hex, newline, 32 hex` with no final newline is also
    # 65 bytes and one line, and `tr -d '\n'` joins it into a perfectly valid 64-hex id — so the
    # size and line checks together still admitted a pointer that is not one hash line.
    [ "$(tail -c 1 "$_ps_ptr" 2>/dev/null | wc -l | tr -d ' ')" = "1" ] || { echo "$_ps_deployed"; return 0; }
    _ps_seal_id="$(tr -d '\n' < "$_ps_ptr" 2>/dev/null)"
    [ "${#_ps_seal_id}" = 64 ] || { echo "$_ps_deployed"; return 0; }
    case "$_ps_seal_id" in
        ""|*[!0-9a-f]*) echo "$_ps_deployed"; return 0 ;;
    esac

    _ps_workshop="$_ps_seal_root/$_ps_seal_id/$_ps_name"
    [ -s "$_ps_workshop" ] || { echo "$_ps_deployed"; return 0; }
    [ -h "$_ps_workshop" ] && { echo "$_ps_deployed"; return 0; }
    # Physically inside the seal: `-s` follows symlinks, so without this a link could hand
    # execution to a file anywhere on the machine.
    _ps_realdir="$(cd -P "$(dirname "$_ps_workshop")" 2>/dev/null && pwd)" || _ps_realdir=""
    [ -n "$_ps_realdir" ] || { echo "$_ps_deployed"; return 0; }
    case "$_ps_realdir/$(basename "$_ps_workshop")" in
        "$_ps_seal_root"/*) ;;
        *) echo "$_ps_deployed"; return 0 ;;
    esac
    # The RESOLVED pathname, so the answer does not depend on symlinks that were followed during
    # checking. ⚠️ This does NOT close the check/use race, and an earlier comment claiming it did
    # was wrong: a resolved path is still a pathname, and anyone who can write the seal root can
    # rename the directory between this line and the hook's `python3`. That is inside the trust
    # root the header describes and `PSK-OL-09` records; it is not defended against here.
    echo "$_ps_realdir/$(basename "$_ps_workshop")"
}

case "${0##*/}" in
    plan-script-path.sh)
        if [ "$#" -ge 1 ]; then
            plan_script "$@"
            exit $?
        fi
        ;;
esac

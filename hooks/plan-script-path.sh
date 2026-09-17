#!/bin/sh
# plan-script-path.sh — which copy of a `plan` script should a hook run?
#
# Sourced, never executed. Defines `plan_script <name> [cwd]`, echoing an absolute path.
#
# **The problem.** Every hook resolved its script against its own location — always `~/dotfiles`,
# the DEPLOYED copy. In the pod where the skill is BUILT that is a contradiction: the gates
# enforcing the contract run last release's code while this release's code is being written, so a
# gate change cannot be exercised end to end without first promoting it to every other pod. You
# cannot develop the gates with the gates.
#
# 🛑 **The trust rule, and it is the whole security model of this file.** A first version selected
# the workshop copy from whatever repository the session happened to be in — "does `cwd`'s repo
# contain `skills/plan/scripts/<name>`?". That is arbitrary code execution: these four hooks fire
# in EVERY session on this machine, so any untrusted checkout containing that path — one cloned to
# read a dependency's source, say — would have its Python executed automatically with the user's
# permissions on the first Read, dispatch or return. MEASURED 2026-09-17 by building such a
# repository; it ran. Found by a Codex review within the hour.
#
# So the builder is **named, never detected**. `plan-builder-root` beside this file holds one
# absolute path, and ONLY that path may supply a workshop script. Any other repository — however
# exactly it mimics the layout — gets the deployed copy. No configuration file means no workshop
# copy anywhere, which is the safe direction.
#
# **Every other uncertainty also falls back to deployed**: an unreadable config, a cwd outside the
# builder, a missing or EMPTY script. A resolution fault must degrade to the behaviour that
# existed before this file, never to "no gate".
#
# **What this does NOT defend against, stated plainly.** The named builder is a TRUST ROOT,
# not a sandbox: its `skills/plan/scripts/` is ordinary mutable working tree, and whatever
# is there executes automatically for any session at or below that path. A compromised or
# careless commit in the builder is therefore a compromise of these four hooks. The rule
# stops an UNRELATED repository from supplying code; it does not make the builder safe.
#
# POSIX sh, no bashisms — one caller is `#!/bin/sh`.

plan_script() {
    _ps_name="$1"
    _ps_cwd="${2:-$PWD}"

    _ps_here="${PLAN_HOOK_DIR:-}"
    if [ -z "$_ps_here" ]; then
        _ps_here="$(cd -P "$(dirname "$0")" 2>/dev/null && pwd)"
    fi
    _ps_deployed="${_ps_here%/hooks}/skills/plan/scripts/$_ps_name"

    # The one repository allowed to supply workshop scripts. Absent or empty -> deployed, always.
    _ps_conf="$_ps_here/plan-builder-root"
    [ -r "$_ps_conf" ] || { echo "$_ps_deployed"; return 0; }
    _ps_builder="$(sed -n '1s/[[:space:]]*$//p' "$_ps_conf" 2>/dev/null)"
    # ABSOLUTE ONLY, and this is a security check, not tidiness. A relative value is resolved by
    # `cd -P` against the SESSION'S cwd, so a config of `.` makes whatever repository the session
    # happens to be in the builder — recreating exactly the arbitrary-repository code execution
    # this file exists to prevent. MEASURED 2026-09-17: it did.
    case "$_ps_builder" in
        /*) ;;
        *) echo "$_ps_deployed"; return 0 ;;
    esac
    _ps_builder="$(cd -P "$_ps_builder" 2>/dev/null && pwd)" || _ps_builder=""
    [ -n "$_ps_builder" ] || { echo "$_ps_deployed"; return 0; }

    # cwd must BE the builder, or sit inside it. Resolved physically, so a symlinked route in
    # cannot masquerade and a relative cwd cannot loop.
    _ps_cwd="$(cd -P "$_ps_cwd" 2>/dev/null && pwd)" || _ps_cwd=""
    [ -n "$_ps_cwd" ] || { echo "$_ps_deployed"; return 0; }
    case "$_ps_cwd" in
        "$_ps_builder"|"$_ps_builder"/*) ;;
        *) echo "$_ps_deployed"; return 0 ;;
    esac

    _ps_workshop="$_ps_builder/skills/plan/scripts/$_ps_name"
    # -s not -f: a zero-length file is a half-written one, and running it would silently disable
    # the gate rather than fail loudly.
    [ -s "$_ps_workshop" ] || { echo "$_ps_deployed"; return 0; }

    # The file must physically LIVE inside the builder. `-s` follows symlinks, so without this a
    # link at skills/plan/scripts/<name> hands execution to a file anywhere on the machine — the
    # named-builder rule enforced on the path but not on the bytes. MEASURED 2026-09-17.
    _ps_realdir="$(cd -P "$(dirname "$_ps_workshop")" 2>/dev/null && pwd)" || _ps_realdir=""
    [ -n "$_ps_realdir" ] || { echo "$_ps_deployed"; return 0; }
    _ps_realfile="$_ps_realdir/$(basename "$_ps_workshop")"
    if [ -h "$_ps_workshop" ]; then
        echo "$_ps_deployed"
        return 0
    fi
    case "$_ps_realfile" in
        "$_ps_builder"/*) ;;
        *) echo "$_ps_deployed"; return 0 ;;
    esac
    echo "$_ps_workshop"
}

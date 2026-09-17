#!/bin/sh
# plan-script-path.sh — which copy of a `plan` script should a hook run?
#
# Sourced, never executed. Defines one function: `plan_script <name> [cwd]`, which echoes an
# absolute path to the script the caller should run.
#
# **The problem this closes.** Every hook resolved its script against its own location —
# `${HOOK_DIR%/hooks}/skills/plan/scripts/<name>` — which is always `~/dotfiles`, the DEPLOYED
# copy. In the pod where the skill is BUILT that is a contradiction: the gates enforcing the
# contract run last release's code while this release's code is being written, so a change to a
# gate cannot be exercised end-to-end without first promoting it to every other pod. Worse, a
# contract change in the workshop copy is judged by a prod hook that has never heard of it. You
# cannot develop the gates with the gates.
#
# **The rule, and it is the same one `preflight.py`'s `copy-in-use` check enforces:** the pod that
# BUILDS the package runs its own copy; every other pod runs the deployed one. A builder is
# detected, never named — `skills/plan/scripts/<name>` present, no `.mirror-of-operation-layer.plan`
# marker beside it, and not resolving to the deployed copy itself (a pod may symlink it for
# convenience, and a link to prod is a consumer).
#
# **Every uncertainty falls back to the deployed copy**, which is exactly the behaviour before
# this file existed. That is deliberate: these hooks fire in every session on the machine, so the
# blast radius of a resolution bug has to be "no change", not "no gate".
#
# POSIX sh. No bashisms — one caller is `#!/bin/sh`.

plan_script() {
    _ps_name="$1"
    _ps_cwd="${2:-$PWD}"

    # The deployed copy: this file's own directory, minus /hooks. Physical, so the dotfiles
    # symlink into ~/.claude/hooks does not resolve into a different tree.
    _ps_here="$(cd -P "$(dirname "$0")" 2>/dev/null && pwd)"
    [ -n "$PLAN_HOOK_DIR" ] && _ps_here="$PLAN_HOOK_DIR"
    _ps_deployed="${_ps_here%/hooks}/skills/plan/scripts/$_ps_name"

    # Walk up from cwd to the repository root.
    _ps_root="$_ps_cwd"
    while [ -n "$_ps_root" ] && [ "$_ps_root" != "/" ]; do
        [ -e "$_ps_root/.git" ] && break
        _ps_root="$(dirname "$_ps_root")"
    done

    _ps_workshop="$_ps_root/skills/plan/scripts/$_ps_name"
    _ps_marker="$_ps_root/skills/.mirror-of-operation-layer.plan"

    if [ -f "$_ps_workshop" ] && [ ! -e "$_ps_marker" ]; then
        _ps_a="$(cd -P "$(dirname "$_ps_workshop")" 2>/dev/null && pwd)"
        _ps_b="$(cd -P "$(dirname "$_ps_deployed")" 2>/dev/null && pwd)"
        if [ -n "$_ps_a" ] && [ "$_ps_a" != "$_ps_b" ]; then
            echo "$_ps_workshop"
            return 0
        fi
    fi
    echo "$_ps_deployed"
}

#!/usr/bin/env bash
# plan-read-guard.sh — PreToolUse (matcher Read): the shim for M1.
#
# Thin by design. The logic lives at ~/dotfiles/skills/plan/scripts/read-guard.py so it
# travels with the skill package and is reviewable as one unit; this file exists only
# because bootstrap.sh symlinks the whole hooks/ directory onto ~/.claude/hooks, so a
# file dropped here is wired by the settings entry alone.
#
# It ALWAYS exits 0. A PreToolUse decision travels in the JSON object on stdout, never in
# the exit code, and a non-zero exit here would surface as a hook error on every Read —
# including the ones the guard means to allow. `|| true` is therefore load-bearing, not
# defensive sloppiness: if the guard itself breaks, reads keep working and the failure is
# visible in the guard's own stderr rather than as a broken session.
set -uo pipefail

HOOK_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN_HOOK_DIR="$HOOK_DIR"; export PLAN_HOOK_DIR
# The resolver is RUN, never sourced: sourcing puts its failure modes (a stray `exit`, a
# syntax error, an unset expansion under `set -u`) inside this hook's process, where a
# pre-defined fallback cannot save them. Deployed is computed first and only replaced by a
# candidate that comes back a real file, so nothing the resolver does reaches this hook
# except one line of stdout.
plan_script() {
    _deployed="${HOOK_DIR%/hooks}/skills/plan/scripts/$1"
    # Pass HOOK_DIR explicitly. Depending on the resolver deriving it from `$0` meant that
    # breaking that derivation disabled sealed resolution in production while every unit
    # test — which injects the argument — stayed green.
    _cand="$(sh "$HOOK_DIR/plan-script-path.sh" "$1" "$PWD" "$HOOK_DIR" 2>/dev/null)" || _cand=""
    if [ -n "$_cand" ] && [ -f "$_cand" ]; then echo "$_cand"; else echo "$_deployed"; fi
}
# Was a hardcoded ~/dotfiles path, which defeated the package's own location derivation and
# pinned this guard to the deployed copy even in the pod that builds it.
PLAN_TARGET="$(plan_script read-guard.py)"
[ -n "$PLAN_TARGET" ] && [ -f "$PLAN_TARGET" ] || PLAN_TARGET="${HOOK_DIR%/hooks}/skills/plan/scripts/read-guard.py"
python3 "$PLAN_TARGET" || true
exit 0

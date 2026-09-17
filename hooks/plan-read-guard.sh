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
# The deployed-copy fallback is defined FIRST, then the resolver is allowed to replace it.
# Order matters: testing `command -v plan_script` AFTER sourcing accepts an inherited
# exported function or any executable of that name on PATH, so ambient code would choose
# which gate runs. Defining it ourselves first, and unsetting anything inherited, means the
# worst case is the behaviour that existed before the resolver did.
unset -f plan_script 2>/dev/null || true
plan_script() { echo "${HOOK_DIR%/hooks}/skills/plan/scripts/$1"; }
[ -r "$HOOK_DIR/plan-script-path.sh" ] && . "$HOOK_DIR/plan-script-path.sh" 2>/dev/null || true
# Was a hardcoded ~/dotfiles path, which defeated the package's own location derivation and
# pinned this guard to the deployed copy even in the pod that builds it.
python3 "$(plan_script read-guard.py)" || true
exit 0

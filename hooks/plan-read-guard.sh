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
# Guarded: a missing, half-written or syntactically broken resolver must not take down
# every session on this machine. If sourcing does not define plan_script, fall back to the
# deployed copy — the behaviour that existed before the resolver did.
[ -r "$HOOK_DIR/plan-script-path.sh" ] && . "$HOOK_DIR/plan-script-path.sh" 2>/dev/null || true
command -v plan_script >/dev/null 2>&1 || \
    plan_script() { echo "${HOOK_DIR%/hooks}/skills/plan/scripts/$1"; }
# Was a hardcoded ~/dotfiles path, which defeated the package's own location derivation and
# pinned this guard to the deployed copy even in the pod that builds it.
python3 "$(plan_script read-guard.py)" || true
exit 0

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

python3 "${HOME}/dotfiles/skills/plan/scripts/read-guard.py" || true
exit 0

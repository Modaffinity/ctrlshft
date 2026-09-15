#!/usr/bin/env bash
# plan-dispatch-gate.sh — PreToolUse (matcher Agent): the shim for M10b.
#
# Thin by design. The logic lives in the skill package at
# skills/plan/scripts/dispatch-gate.py so it travels with the skill and is reviewable as
# one unit; this file exists only because bootstrap.sh symlinks the whole hooks/ directory
# onto ~/.claude/hooks, so a file dropped here is wired by the settings entry alone.
#
# It ALWAYS exits 0. A PreToolUse decision travels in the JSON object on stdout, never in
# the exit code, and a non-zero exit here would surface as a hook error on every Agent
# dispatch — including the ones the gate means to allow. `|| true` is therefore
# load-bearing: if the gate itself breaks, dispatching keeps working and the failure is
# visible in the gate's own stderr rather than as a session that cannot spawn anything.
#
# The package path is derived from this file's own PHYSICAL location, not from $HOME:
# bootstrap.sh symlinks hooks/ onto ~/.claude/hooks, so a logical `..` from the invoked
# path would land in ~/.claude/skills, which is a different tree.
set -uo pipefail

HOOK_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${HOOK_DIR%/hooks}/skills/plan/scripts/dispatch-gate.py" || true
exit 0

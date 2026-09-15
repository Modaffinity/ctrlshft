#!/usr/bin/env bash
# plan-status-export.sh — statusLine: the shim for M3.
#
# `statusLine` currently points at $HOME/.claude/statusline-command.sh, which does not
# exist (MEASURED, SPEC.md § 4.2) — so there is no renderer to pass through and nothing
# is being replaced. This script is the *only* statusLine command: it reads the
# statusLine input JSON on stdin, exports it (plus its own last-write time) to
# ~/.claude/plan-guard/context/<session_id>.json and ~/.claude/plan-guard/seats.json for
# T9 and T13 to read, then composes and prints the status line itself.
#
# Logic lives inline (not in <pkg>/scripts/) — this task's own Files list names only this
# one file. json is stdlib-only, so the JSON handling shells out to python3 (3.9 stdlib,
# per Global constraint 6) rather than parsing JSON in bash.
#
# Wiring — repointing `statusLine` at this script in both settings files — is T10's, not
# this task's (R173). This script only composes correctly once fed a payload.
set -uo pipefail

python3 -c '
import json
import os
import sys
import time

raw = sys.stdin.read()
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    data = {}

if not isinstance(data, dict):
    data = {}

now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
session_id = data.get("session_id") or "unknown"

base = os.path.expanduser("~/.claude/plan-guard")
context_dir = os.path.join(base, "context")
os.makedirs(context_dir, exist_ok=True)

# A stale file is *no reading*, never zero (requirement 4) — the recorded write time is
# what lets a consumer tell "no export happened recently" from "the field is genuinely 0".
record = dict(data)
record["_exported_at"] = now

with open(os.path.join(context_dir, f"{session_id}.json"), "w") as f:
    json.dump(record, f)

with open(os.path.join(base, "seats.json"), "w") as f:
    json.dump(record, f)


def render(value):
    # Never an invented zero: an absent field renders as a literal "-".
    return "-" if value is None else value


context_window = data.get("context_window") or {}
cost = data.get("cost") or {}
rate_limits = data.get("rate_limits") or {}
seven_day = rate_limits.get("seven_day") or {}

used_pct = render(context_window.get("used_percentage"))
total_cost = render(cost.get("total_cost_usd"))
seven_day_pct = render(seven_day.get("used_percentage"))

print(f"plan-guard {used_pct}% ctx · ${total_cost} · 7d {seven_day_pct}%")
'

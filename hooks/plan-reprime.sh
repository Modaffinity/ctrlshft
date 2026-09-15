#!/usr/bin/env bash
# plan-reprime.sh — SessionStart: M5, the successor of a cleared session is handed its
# context by the harness, not by a human paste (SPEC.md § 4.3 step 6, § 17.8).
#
# Fires on every SessionStart source (startup, resume, clear, compact, fork) — requirement 1
# is the whole safety property: exit silently on any `source` other than `clear`, so every
# other session start on this machine is untouched. On `clear`, it resolves the live
# workstream by the SAME discriminator T3's read-guard.py uses (a non-archive
# `plans/*/STATE.md` with `session: build`, no `guard: off`), finds the newest
# `plans/<slug>/notes/handoff/*-HANDOFF.md`, and emits its text as `additionalContext`.
# The handoff text is a pointer, never a payload — its shipped form is SPEC.md § 17.8 and
# T9 writes it; this script only delivers it. No live workstream, or no handoff file, is
# not an error: a session start must never be blocked by an absent handoff.
#
# Logic lives inline (not in <pkg>/scripts/) — this task's Files list names only this one
# script. json is stdlib-only, so JSON handling shells out to python3 (3.9 stdlib, per
# Global constraint 6), matching plan-status-export.sh's (M3) shape.
#
# Wiring — pointing SessionStart at this script in both settings files — is T10's, not this
# task's (R173).
set -uo pipefail

python3 -c '
import glob
import json
import os
import sys


def frontmatter(path):
    """The leading `---` block as a dict, or an empty dict — read as frontmatter, never
    grepped, exactly as read-guard.py (T3) does it, so the two scripts agree on what a
    live workstream is."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            if fh.readline().rstrip("\n") != "---":
                return {}
            out = {}
            for line in fh:
                line = line.rstrip("\n")
                if line.strip() == "---":
                    return out
                key, sep, value = line.partition(":")
                if sep:
                    out[key.strip()] = value.strip()
            return {}
    except (OSError, UnicodeError):
        return {}


def repo_root(cwd):
    """The nearest ancestor of `cwd` holding a `.git` entry, or None."""
    path = os.path.realpath(cwd)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def live_workstream(root):
    """The first non-archive `plans/*/STATE.md` whose frontmatter says `session: build`
    without `guard: off` — (slug, plan dir, state path), or None. Two live workstreams is
    a lawful state (T6); this picks the alphabetically-first slug deterministically rather
    than guessing which one the operator means."""
    plans = os.path.join(root, "plans")
    try:
        names = sorted(os.listdir(plans))
    except OSError:
        return None
    for name in names:
        if name == "archive":
            continue
        plan_dir = os.path.join(plans, name)
        state = os.path.join(plan_dir, "STATE.md")
        if not os.path.isfile(state):
            continue
        meta = frontmatter(state)
        if meta.get("session") == "build" and meta.get("guard") != "off":
            return name, plan_dir, state
    return None


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0

    if payload.get("source") != "clear":            # requirement 1 — the safety property
        return 0

    cwd = payload.get("cwd")
    if not cwd:
        return 0

    root = repo_root(cwd)
    if root is None:
        return 0

    found = live_workstream(root)
    if found is None:
        return 0
    _slug, plan_dir, state_path = found

    # <ts>-HANDOFF.md — ts is `%Y%m%d-%H%M%SZ` (codex-run.sh, T2s convention), so a lexical
    # sort orders chronologically and the last entry is the newest.
    handoff_dir = os.path.join(plan_dir, "notes", "handoff")
    candidates = sorted(glob.glob(os.path.join(handoff_dir, "*-HANDOFF.md")))

    if candidates:
        with open(candidates[-1], encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    else:
        # requirement 4 — an absent handoff is not an error and must not block the start.
        text = "No handoff file found for %s; resume from STATE.md directly." % state_path

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": text}}))
    return 0


sys.exit(main())
'

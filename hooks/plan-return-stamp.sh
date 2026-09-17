#!/usr/bin/env bash
# plan-return-stamp.sh — PostToolUse, matcher `Task|Agent`: M2b, the SECOND NET.
#
# M2's SubagentStop gate is primary and it has a measured hole: the block count is capped
# by CLAUDE_CODE_STOP_HOOK_BLOCK_CAP, default 8, so a determinedly invalid return gets
# through on the ninth. This is the net behind it, and it works differently on purpose —
# PostToolUse runs AFTER the dispatch has returned, so it cannot block anything. What it
# does instead is make the rejection unreadable-around: it stamps the reason into
# `hookSpecificOutput.additionalContext`, so the orchestrator cannot read an unvalidated
# `done` without also reading why it is not one. That is the choice B6 exercised, removed.
#
# Two jobs, both carried on every matched dispatch (SPEC.md § 6.1 R156, § 4.3a):
#
#   (a) the return gate — the completed tool call's response text is written out and
#       `return-gate.py` is run over it IN FILE MODE. Not hook mode, and the reason is
#       structural rather than stylistic (X6): hook mode takes `transcript_path` from its
#       payload, and a PostToolUse payload carries the tool's inputs and response and no
#       transcript path at all, so the two modes have no field in common. File mode is
#       also the mode every M2 criterion exercises, so this net is proven by those tests.
#   (b) the liveness stamp — the same line M2 blocks the stop on. A supervisor nobody
#       started protects nothing, and its absence is made loud in both nets rather than
#       once.
#
# Rejections are appended to ~/.plan-guard/rejects/<session_id>.log (requirement 4).
# File mode does not log — only hook mode does — so the append is this shim's job.
#
# Four decisions that are measured or scoped rather than chosen, and all four are
# load-bearing:
#
#   * `tool_response` is the field the harness actually ships. SPEC.md § 6.1 writes the
#     prose name `response`; the harness's own embedded hook documentation ships
#     `"tool_response": { ... }  // PostToolUse only`. BOTH spellings are read, because a
#     net that reads the wrong one is indistinguishable from a clean dispatch.
#   * the matcher alternation is checked HERE as well as in the wiring, so a mis-wired or
#     empty matcher cannot turn every Bash call into a return-gate run. The order is
#     `Task|Agent` and it is measured: across every other session's transcripts on this
#     machine `Agent` appears 1,052 times and `Task` 0, so `Agent` is the known-present
#     alternative and CHECKS.md rule 1 puts it LAST — a first-position control passes on
#     an implementation that reaches only the first alternative.
#   * the net is scoped by § 3.1's discriminator, reused: a repository holding a live
#     `session: build` workstream not carrying `guard: off`. Without it every `Agent`
#     dispatch anywhere on this machine would be gated against a plan that does not
#     exist, and `ambiguous plan (0 matches)` would be stamped onto unrelated work.
#   * `--plan` is handed the REPOSITORY ROOT, not a path this shim globbed itself. The
#     gate owns the glob and owns the refusal when it matches other than one file, so the
#     ambiguity branch is the gate's single implementation rather than a second one here.
#
# It never blocks and never fails the dispatch: every path exits 0. A net that could break
# a legitimate dispatch would be traded away the first time it misfired.
#
# The scratch root is `${TMPDIR:-/tmp}/plan-return-stamp-$$`, unique per invocation,
# because `$SCRATCH` is NOT an environment variable and nothing a hook executes may
# reference it. The package path comes from this file's own PHYSICAL location, not from
# $HOME: bootstrap.sh symlinks hooks/ onto ~/.claude/hooks, so a logical `..` from the
# invoked path lands in a different tree. $HOME is then free to mean the plan-guard root.
set -uo pipefail

HOOK_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The environment is the session's, so a `sh` or `python3` earlier in PATH — or a BASH_ENV
# file, or an exported shell function of that name — chooses what runs. Absolute
# interpreters and a cleared BASH_ENV close the cheap versions of that.
unset BASH_ENV ENV 2>/dev/null || true
unset -f sh python3 2>/dev/null || true
PLAN_SH=/bin/sh
[ -x "$PLAN_SH" ] || PLAN_SH=sh
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
    _cand="$("$PLAN_SH" "$HOOK_DIR/plan-script-path.sh" "$1" "$PWD" "$HOOK_DIR" 2>/dev/null)" || _cand=""
    if [ -n "$_cand" ] && [ -f "$_cand" ]; then echo "$_cand"; else echo "$_deployed"; fi
}
GATE="$(plan_script return-gate.py)"
# Never run an empty or missing path: a resolver that declines (a malformed script
# name) returns nothing, and `python3 ""` is a confusing failure rather than a gate.
[ -n "$GATE" ] && [ -f "$GATE" ] || GATE="${HOOK_DIR%/hooks}/skills/plan/scripts/return-gate.py"

ROOT="${TMPDIR:-/tmp}/plan-return-stamp-$$"
mkdir -p "$ROOT" || exit 0
trap 'rm -rf "$ROOT"' EXIT
PAYLOAD="$ROOT/payload.json"
cat > "$PAYLOAD"

python3 - "$PAYLOAD" "$GATE" "$ROOT" <<'PY'
import json
import os
import subprocess
import sys
import time
from datetime import datetime

WINDOW = 120.0                  # SPEC.md § 4.3a, seconds
MATCHER = ("Task", "Agent")     # requirement 1, in that order


def frontmatter(path):
    """The leading `---` block as a dict. Parsed as frontmatter, never grepped: a ledger
    that quotes the words `session: build` in prose is not a live build workstream."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            if fh.readline().rstrip("\n") != "---":
                return {}
            out = {}
            for line in fh:
                if line.strip() == "---":
                    return out
                key, sep, value = line.rstrip("\n").partition(":")
                if sep:
                    out[key.strip()] = value.strip()
            return {}
    except (OSError, UnicodeError):
        return {}


def repo_root(cwd):
    path = os.path.realpath(cwd)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def live_slugs(root):
    """Every live build workstream in `root` — § 3.1's discriminator, reused."""
    plans = os.path.join(root, "plans")
    try:
        names = sorted(os.listdir(plans))
    except OSError:
        return []
    out = []
    for name in names:
        if name == "archive":
            continue
        meta = frontmatter(os.path.join(plans, name, "STATE.md"))
        if meta.get("session") == "build" and meta.get("guard") != "off":
            out.append(name)
    return out


def age(value):
    """Seconds since `value`, which the supervisor may write as epoch seconds or as an
    ISO-8601 stamp; None when it is absent or unreadable, and None is stamped."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return time.time() - float(value)
    if not isinstance(value, str):
        return None
    text = value.strip()
    try:
        return time.time() - float(text)
    except ValueError:
        pass
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.astimezone()
    return time.time() - stamp.timestamp()


def response_text(value):
    """The return text out of whatever shape the tool response arrived in — a string, a
    content-block list, or an object wrapping either. Anything else yields '', which is
    silence rather than a guess."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for block in value:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(p for p in parts if p)
    if isinstance(value, dict):
        for key in ("content", "text", "output", "result"):
            if key in value:
                return response_text(value[key])
    return ""


def log_reject(home, session_id, line):
    """Requirement 4. A log that cannot be written is never a reason to drop the stamp —
    the stamp is the mechanism, the log is the record of it."""
    try:
        folder = os.path.join(home, ".plan-guard", "rejects")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "%s.log" % (session_id or "unknown")), "a",
                  encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), line))
    except OSError:
        pass


payload_path, gate, root = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(payload_path, encoding="utf-8") as fh:
        payload = json.load(fh)
except (OSError, ValueError):
    payload = {}
if not isinstance(payload, dict):
    payload = {}

if payload.get("tool_name") not in MATCHER:
    sys.exit(0)

raw = payload.get("tool_response")
if raw is None:
    raw = payload.get("response")
text = response_text(raw)
if not text.strip():
    sys.exit(0)

repo = repo_root(payload.get("cwd") or os.getcwd())
slugs = live_slugs(repo) if repo else []
if not slugs:
    sys.exit(0)

home = os.path.expanduser("~")
lines = []

# (a) the return gate, in file mode
ret = os.path.join(root, "ret.txt")
with open(ret, "w", encoding="utf-8") as fh:
    fh.write(text)
try:
    res = subprocess.run([sys.executable, gate, "--return", ret, "--plan", repo],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    verdict = res.stdout.decode("utf-8", "replace").strip()
    rejected = res.returncode != 0
except OSError as exc:
    verdict, rejected = "RETURN-GATE: did not run (%s)" % exc, True
if rejected and verdict:
    lines.append(verdict)
    log_reject(home, payload.get("session_id"), verdict)

# (b) the liveness stamp
for slug in slugs:
    state = os.path.join(home, ".plan-guard", "state", "%s.json" % slug)
    try:
        with open(state, encoding="utf-8") as fh:
            beat = json.load(fh).get("heartbeat")
    except (OSError, ValueError):
        beat = None
    seconds = age(beat)
    if seconds is None or seconds > WINDOW:
        lines.append("PLAN-SUPERVISOR: not running (no heartbeat since %s) — start it "
                     "before continuing." % ("never" if beat is None else beat))

if lines:
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "\n".join(lines)}}) + "\n")
PY

exit 0

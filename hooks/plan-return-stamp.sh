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
PLAN_PY=/usr/bin/python3
[ -x "$PLAN_PY" ] || PLAN_PY=python3
PLAN_PY_ISO="-I"
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

# Exclusive creation, and cleanup only for a name this process made. `mkdir -p` succeeds
# on a pre-existing directory — including a planted symlink — and the old unconditional
# `rm -rf` then deleted it as though this process had created it.
# Candidate parents are tried through to a CREATED directory, not just a writable-looking
# parent. Round five stopped at the first parent passing -d/-w/-!h and then exited if the
# exclusive mkdir failed there — so one unusable first candidate (quota, ENOSPC, an ACL -w does
# not reflect, a pre-planted predictable name) took out the whole chain while a perfectly good
# HOME or /tmp was never attempted.
ROOT=""
for _cand in "${TMPDIR:-}" "${HOME:-}/.plan-guard/tmp" /tmp; do
    [ -n "$_cand" ] || continue
    mkdir -p "$_cand" 2>/dev/null || continue
    [ -d "$_cand" ] && [ -w "$_cand" ] && [ ! -h "$_cand" ] || continue
    # EXCLUSIVE: `mkdir -p` succeeds on a name that already exists, including a planted
    # symlink, and cleanup then deletes it as though this process had made it.
    _try="$_cand/plan-return-stamp-$$-$(date +%s 2>/dev/null || echo 0)"
    if mkdir "$_try" 2>/dev/null; then
        PLAN_TMP_PARENT="$_cand"; ROOT="$_try"; break
    fi
done
[ -n "$ROOT" ] || exit 0
cleanup_scratch_dir () {
    case "$ROOT" in
        # The FULL prefix this script constructed, never a wildcard that a
        # neighbouring name could satisfy. Nothing is removed whose name we
        # did not build ourselves.
        "$PLAN_TMP_PARENT"/plan-return-stamp-$$-*)
            [ -d "$ROOT" ] && [ ! -h "$ROOT" ] && rm -rf "$ROOT" ;;
    esac
}
trap cleanup_scratch_dir EXIT
PAYLOAD="$ROOT/payload.json"
cat > "$PAYLOAD"

"$PLAN_PY" $PLAN_PY_ISO - "$PAYLOAD" "$GATE" "$ROOT" <<'PY'
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from datetime import datetime

WINDOW = 120.0                  # SPEC.md § 4.3a, seconds
SKEW = 60.0                     # a heartbeat may sit slightly ahead of this
                                # clock; past that it is not skew.
MATCHER = ("Task", "Agent")     # requirement 1, in that order


FRONTMATTER_CAP = 64 * 1024     # a real STATE.md header is a few hundred bytes


def frontmatter(path):
    """The leading `---` block as a dict. Parsed as frontmatter, never grepped: a ledger
    that quotes the words `session: build` in prose is not a live build workstream.

    This path is REPOSITORY-CONTROLLED, which the unbounded read here ignored until
    2026-09-17. A FIFO committed at `plans/x/STATE.md` blocked the open forever and a symlink
    to `/dev/zero` never reached EOF, so a repository could hang or exhaust the hook before any
    gate ran — a denial of service needing nothing but a file in the tree. `lstat` first (a
    symlink is not a regular file and is refused as one), then a capped read.
    """
    try:
        info = os.lstat(path)
    except OSError:
        return {}
    if not stat.S_ISREG(info.st_mode):
        return {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(FRONTMATTER_CAP)
    except (OSError, UnicodeError):
        return {}
    lines = head.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        return {}
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return out
        key, sep, value = line.rstrip("\r").partition(":")
        if sep:
            out[key.strip()] = value.strip()
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
    # `-I` on the CHILD too. The outer interpreter runs isolated, but a nested
    # `[sys.executable, gate]` starts a FRESH one that does not: measured 2026-09-17,
    # sys.flags.isolated == 0. With PYTHONPATH naming the untrusted repository, its
    # sitecustomize.py then ran as the operator on every stamped dispatch — the exact
    # exposure the isolation fix claimed to close, one process further down.
    res = subprocess.run([sys.executable, "-I", gate, "--return", ret, "--plan", repo],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    verdict = res.stdout.decode("utf-8", "replace").strip()
    rejected = res.returncode != 0
except OSError as exc:
    verdict, rejected = "RETURN-GATE: did not run (%s)" % exc, True
if rejected:
    # A rejection with NOTHING on stdout used to be dropped: `rejected and verdict` was
    # false, no line was appended, and the whole second net vanished silently. A gate that
    # exits non-zero has rejected the return whether or not it managed to say why, and
    # "it failed and said nothing" is itself the thing the operator needs told.
    if not verdict:
        verdict = ("RETURN-GATE: REJECTED — the gate exited %s without a verdict; treat "
                   "this return as unverified." % res.returncode)
    lines.append(verdict)
    log_reject(home, payload.get("session_id"), verdict)

# (b) the liveness stamp
for slug in slugs:
    # Keyed by repository AND slug. On slug alone the heartbeat was a GLOBAL name: two
    # checkouts both holding a live workstream of the same name shared one file, so a
    # supervisor watching the first satisfied this gate in the second. The digest must match
    # plan-supervisor.py state_name() and plan-subagent-hook.sh exactly.
    #
    # THE UNKEYED NAME IS STILL READ, and that is the dev/prod split rather than backward
    # compatibility. These hooks are GLOBAL — one copy fires in every session on this machine —
    # while the supervisor is versioned per pod: this pod runs the workshop copy, every other
    # pod runs the released one, which writes the old name. Reading only the new name would have
    # blocked every subagent return in every other pod from the moment these hooks landed.
    # The fallback carries the old collision risk for pods still on the released supervisor,
    # exactly as before and no worse; it protects nothing less than it did yesterday, and it
    # goes dead of its own accord when release 4 is promoted.
    digest = hashlib.sha256(os.path.realpath(repo).encode("utf-8")).hexdigest()[:12]
    folder = os.path.join(home, ".plan-guard", "state")
    beat = None
    for name in ("%s--%s.json" % (slug, digest), "%s.json" % slug):
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                beat = json.load(fh).get("heartbeat")
            break
        except (OSError, ValueError):
            continue
    seconds = age(beat)
    # The SAME range the SubagentStop hook enforces. This file kept the bare upper bound
    # through round five: NaN compares False against everything, so `seconds > WINDOW` was
    # False and a NaN heartbeat read as live here while the other hook blocked it. A fix
    # that lands in one of two call sites is not a fix.
    if seconds is None or seconds != seconds or seconds > WINDOW or seconds < -SKEW:
        lines.append("PLAN-SUPERVISOR: not running (no heartbeat since %s) — start it "
                     "before continuing." % ("never" if beat is None else beat))

if lines:
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "\n".join(lines)}}) + "\n")
PY

exit 0

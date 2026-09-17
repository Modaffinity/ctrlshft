#!/usr/bin/env bash
# plan-subagent-hook.sh — SubagentStop: M2's shim, and it carries THREE jobs.
#
#   (a) the return gate — `return-gate.py --hook`, and a rejection blocks the stop with
#       exit 2 so the reason reaches the subagent and it re-emits (SPEC.md § 6.1);
#   (b) the boundary marker — one JSON line per stop into
#       ~/.plan-guard/boundary/<session_id>.jsonl, which is the live, harness-
#       executed signal the supervisor bands on (§ 4.2);
#   (c) liveness — a supervisor nobody started protects nothing, so its ABSENCE blocks
#       the stop rather than passing quietly (§ 4.3a). An absent state file blocks too;
#       that is intended and is not softened here.
#
# Two behaviours that are measured rather than chosen, and both are load-bearing:
#
#   * `stop_hook_active` is a real input field and the harness's own guidance is to
#     return success while it is true. Job (b) still runs — a boundary happened — but
#     nothing blocks, so this gate cannot loop. The block count is separately capped by
#     CLAUDE_CODE_STOP_HOOK_BLOCK_CAP, default 8, which means a determinedly invalid
#     return gets through on the ninth. That hole is M2b's, not this file's.
#   * the scratch root is `${TMPDIR:-/tmp}`, unique per invocation, because `$SCRATCH` is
#     NOT an environment variable and nothing a hook executes may reference it.
#
# The package path is derived from this file's own PHYSICAL location, not from $HOME:
# bootstrap.sh symlinks the whole hooks/ directory onto ~/.claude/hooks, so a logical
# `..` from the invoked path would land in ~/.claude/skills, which is a different tree.
# $HOME is then free to be exactly what it means here — the plan-guard state root.
set -uo pipefail

HOOK_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Absolute, isolated interpreters stop PATH choosing what runs.
# ⚠️ This does NOT close BASH_ENV or exported shell functions: bash reads BASH_ENV
# BEFORE line one of this file, and an exported `dirname` or `cd` runs before any
# `unset -f` here. Sanitising from inside the hook cannot work; it belongs in whatever
# launches hooks. Setting those already implies code execution, so it is ambient
# rather than a hole this file opened — recorded, not claimed closed.
unset BASH_ENV ENV 2>/dev/null || true
unset -f sh python3 2>/dev/null || true
PLAN_SH=/bin/sh
[ -x "$PLAN_SH" ] || PLAN_SH=sh
PLAN_PY=/usr/bin/python3
[ -x "$PLAN_PY" ] || PLAN_PY=python3
# `-I` ignores PYTHONPATH/PYTHONHOME, user site-packages and sitecustomize, and drops
# the CWD from sys.path — so an untrusted repository cannot supply importable code to
# the gate. Absolute alone did not isolate anything.
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
# The pod that BUILDS this skill runs its own copy; everyone else runs the deployed one, and
# any doubt falls back to deployed. See plan-script-path.sh.
GATE="$(plan_script return-gate.py)"
# Never run an empty or missing path: a resolver that declines (a malformed script
# name) returns nothing, and `python3 ""` is a confusing failure rather than a gate.
[ -n "$GATE" ] && [ -f "$GATE" ] || GATE="${HOOK_DIR%/hooks}/skills/plan/scripts/return-gate.py"

# Scratch, and BOTH failure directions matter here.
#
# `mkdir -p "$ROOT" || exit 0` failed OPEN: with TMPDIR=/dev/null the hook returned 0 before the
# return gate, the boundary marker or the liveness check ran, so an invalid stage return sailed
# through. MEASURED 2026-09-17.
#
# Its first replacement then failed the other way, twice over. `mktemp -d` under `$TMPDIR` is a
# DENIAL OF SERVICE on the operator's own run — one inherited TMPDIR=/dev/null blocks every VALID
# return — and worse, `trap 'rm -rf "$ROOT"'` made a destructive command depend on untrusted
# output: an exported `mktemp` shell function returning `$HOME` would have had this hook delete
# the home directory. A fix that introduces `rm -rf` on an attacker-chosen path is not a fix.
#
# So: try several roots, build the path OURSELVES, and never remove anything whose name we did
# not construct.
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
    _try="$_cand/plan-subagent-$$-$(date +%s 2>/dev/null || echo 0)"
    if mkdir "$_try" 2>/dev/null; then
        PLAN_TMP_PARENT="$_cand"; ROOT="$_try"; break
    fi
done
if [ -z "$ROOT" ]; then
    echo "RETURN-GATE: BLOCKED — no private scratch directory could be created; the gate could not run" >&2
    exit 2
fi
cleanup_scratch_dir () {
    case "$ROOT" in
        # The FULL prefix this script constructed, never a wildcard that a
        # neighbouring name could satisfy. Nothing is removed whose name we
        # did not build ourselves.
        "$PLAN_TMP_PARENT"/plan-subagent-$$-*)
            [ -d "$ROOT" ] && [ ! -h "$ROOT" ] && rm -rf "$ROOT" ;;
    esac
}
trap cleanup_scratch_dir EXIT
PAYLOAD="$ROOT/payload.json"
# A failed write used to be ignored, so a planted readable payload could stand in
# for the real one — `stop_hook_active: true` in it makes this hook print SKIP.
cat > "$PAYLOAD" || { echo "RETURN-GATE: BLOCKED — cannot write the payload" >&2; exit 2; }

# Jobs (b) and (c). One line on stdout: SKIP, OK, or "BLOCK <message>".
VERDICT="$("$PLAN_PY" $PLAN_PY_ISO - "$PAYLOAD" <<'PY'
import hashlib
import json
import os
import stat
import sys
import time
from datetime import datetime

WINDOW = 120.0          # SPEC.md § 4.3a, seconds
SKEW = 60.0             # a heartbeat may sit slightly in the future; beyond this it
                        # is not clock skew, it is a stamp no real clock produced.
                        # (No apostrophe here on purpose: this heredoc sits inside a
                        # command substitution, and bash mis-parses a lone quote in it.)


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
    ISO-8601 stamp; None when it is absent or unreadable, and None blocks."""
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


try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        payload = json.load(fh)
except (OSError, ValueError):
    payload = {}
if not isinstance(payload, dict):
    payload = {}

home = os.path.expanduser("~")
session = payload.get("session_id")

# (b) the boundary marker
folder = os.path.join(home, ".plan-guard", "boundary")
os.makedirs(folder, exist_ok=True)
with open(os.path.join(folder, "%s.jsonl" % (session or "unknown")), "a",
          encoding="utf-8") as fh:
    fh.write(json.dumps({"ts": datetime.now().astimezone().isoformat(),
                         "session_id": session,
                         "agent_id": payload.get("agent_id")}) + "\n")

if payload.get("stop_hook_active"):
    print("SKIP")
    sys.exit(0)

# (c) liveness
root = repo_root(payload.get("cwd") or os.getcwd())
for slug in (live_slugs(root) if root else []):
    # Keyed by repository AND slug. On slug alone the heartbeat was a GLOBAL name: two
    # checkouts both holding a live workstream of the same name shared one file, so a
    # supervisor watching the first satisfied this gate in the second. The digest must match
    # plan-supervisor.py state_name() and plan-return-stamp.sh exactly.
    #
    # THE UNKEYED NAME IS STILL READ, and that is the dev/prod split rather than backward
    # compatibility. These hooks are GLOBAL — one copy fires in every session on this machine —
    # while the supervisor is versioned per pod: this pod runs the workshop copy, every other
    # pod runs the released one, which writes the old name. Reading only the new name would have
    # blocked every subagent return in every other pod from the moment these hooks landed.
    # The fallback carries the old collision risk for pods still on the released supervisor,
    # exactly as before and no worse; it protects nothing less than it did yesterday, and it
    # goes dead of its own accord when release 4 is promoted.
    digest = hashlib.sha256(os.path.realpath(root).encode("utf-8")).hexdigest()[:12]
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
    # A RANGE, not just an upper bound. JSON permits NaN and Python parses it, and every
    # comparison against NaN is False — so `seconds > WINDOW` was False and a heartbeat of NaN
    # passed liveness. A far-future stamp gives a large negative age and passed the same way.
    # Fail-closed means the age must be a finite number inside an explicit window.
    if seconds is None or seconds != seconds or seconds > WINDOW or seconds < -SKEW:
        print("BLOCK PLAN-SUPERVISOR: not running (no heartbeat since %s) — start it "
              "before continuing." % ("never" if beat is None else beat))
        sys.exit(0)
print("OK")
PY
)"
if [ $? -ne 0 ] || [ -z "$VERDICT" ]; then
    printf 'PLAN-SUBAGENT-HOOK: the boundary and liveness step did not run — supervisor liveness is unverified.\n' >&2
    exit 2
fi

[ "$VERDICT" = "SKIP" ] && exit 0

# (a) the return gate. It prints its own RETURN-GATE: line on stderr.
"$PLAN_PY" $PLAN_PY_ISO "$GATE" --hook < "$PAYLOAD"
gate_rc=$?
blocked=0
if [ "$gate_rc" -ne 0 ]; then
    blocked=1
fi

case "$VERDICT" in
    "BLOCK "*)
        printf '%s\n' "${VERDICT#BLOCK }" >&2
        blocked=1
        ;;
esac

if [ "$blocked" -eq 1 ]; then
    exit 2
fi
exit 0

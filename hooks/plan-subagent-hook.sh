#!/usr/bin/env bash
# plan-subagent-hook.sh — SubagentStop: M2's shim, and it carries THREE jobs.
#
#   (a) the return gate — `return-gate.py --hook`, and a rejection blocks the stop with
#       exit 2 so the reason reaches the subagent and it re-emits (SPEC.md § 6.1);
#   (b) the boundary marker — one JSON line per stop into
#       ~/.plan-guard/boundary/<session_id>.jsonl, which is the live, harness-
#       executed signal the supervisor bands on (§ 4.2);
#   (c) liveness — a supervisor nobody started protects nothing, so its ABSENCE blocks
#       the stop rather than passing quietly (§ 4.3a).
#
# WHICH WORKSTREAMS JOB (c) COVERS COMES FROM THE SUPERVISOR, NOT FROM THE REPOSITORY.
# Until 2026-09-17 both this hook and the PostToolUse net answered that by reading
# `plans/*/STATE.md` out of the working directory — which is the untrusted repository, the
# very thing being gated. Eight review rounds each found a bypass or a denial of service in
# that code, and they were all one shape: a pipe that hung the open, a symlink to /dev/zero
# that never ended, two different size caps that hid a workstream, a CR-only header that hid
# one in 23 bytes, a hundred symlinks to one big file, and `guard: off` written by the
# repository itself. A scope taken from the thing being gated cannot be made safe by parsing
# it more carefully.
#
# So the supervisor now REGISTERS its pod in ~/.plan-guard/state/, and `registrations()`
# reads that. Nothing in job (c) opens a file the repository controls. Registration creates
# the obligation and outlives the supervisor — a dead heartbeat still blocks, which is the
# case this gate exists for — and only `plan-supervisor.py --unregister` lifts it, replacing
# the `guard: off` line that used to sit inside the gated tree. An UNREGISTERED directory is
# not doing plan work and is not gated by (c); job (a) still runs there, unconditionally.
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


def registrations(home, cwd):
    """Every workstream a supervisor has REGISTERED whose pod contains `cwd`.

    This replaces reading `plans/*/STATE.md` out of the working directory, and the change is
    the point rather than an optimisation. The working directory is an untrusted repository —
    it is the thing being gated — and deriving the gate's SCOPE from it left no safe direction:
    fail open on a malformed header and the repository hides its own workstream; fail closed and
    any repository stops every subagent return by committing one absurd file. Eight review rounds
    produced a bypass or a denial of service in that code every single time, and they were all
    one shape. PSK-OL-12.

    So the obligation is now recorded where the gated repository cannot write: the supervisor
    stamps `pod` into `~/.plan-guard/state/`, and this reads that. Nothing here opens a file the
    repository controls, which is why a pipe, a symlink to /dev/zero, an oversized header, a
    CR-only header and a hundred symlinks to one big file are not defended against one by one —
    the code that could be hurt by them is gone.

    Registration creates the obligation and OUTLIVES the supervisor: a state file with a dead
    heartbeat still means work here must be supervised, which is exactly the case the gate
    exists for. Only `--unregister` lifts it.
    """
    folder = os.path.join(home, ".plan-guard", "state")
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    here = os.path.realpath(cwd)
    out = []
    for name in names:
        if not name.endswith(".json"):
            continue
        record = read_record(os.path.join(folder, name))
        if record is None:
            continue
        pod = record.get("pod")
        if not isinstance(pod, str) or not pod:
            continue
        pod = os.path.realpath(pod)
        if here == pod or here.startswith(pod + os.sep):
            out.append({"slug": record.get("slug") or name[:-len(".json")],
                        "heartbeat": record.get("heartbeat"), "pod": pod})
    # Most specific first. Picking by filename order handed the return of a child pod to
    # the ancestor plan when one registration sits inside another. (No apostrophe in this
    # comment on purpose: the block is a heredoc inside a command substitution, and bash
    # mis-parses a lone quote there. Seventh time today.)
    out.sort(key=lambda r: len(r["pod"]), reverse=True)
    return out


RECORD_CAP = 1 << 20


def read_record(path):
    """One state record, or None. Bounded, non-blocking, never through a symlink.

    Hardened even though ~/.plan-guard/ is the operator tree: a subagent runs under the operator
    UID, so it can plant a FIFO or a link to /dev/zero among these records and hang the gate
    before it runs. This makes that a skipped record rather than a stop that never returns.
    Must match paths.py registrations()/_read_record.
    """
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return None
        want = min(info.st_size, RECORD_CAP) or RECORD_CAP
        buf = b""
        while len(buf) < want:
            block = os.read(fd, want - len(buf))
            if not block:
                break
            buf += block
    except OSError:
        return None
    finally:
        os.close(fd)
    try:
        record = json.loads(buf.decode("utf-8", "replace"))
    except ValueError:
        return None
    return record if isinstance(record, dict) else None


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

regs = registrations(home, payload.get("cwd") or os.getcwd())

# ⚠️ SCOPE, and its absence was a MACHINE-WIDE DENIAL OF SERVICE. Job (a) ran on every subagent
# stop in every project on this machine, and `return-gate.py --hook` has never had a scope check
# of its own — so an ordinary prose answer in a repository with no plans came back
# "REJECTED — no VERDICT line", exit 2, and the subagent was blocked until the harness block cap
# released it on the ninth try. MEASURED 2026-09-17 in a temporary repository holding one README.
#
# It predates this release, and the fix belongs HERE rather than only in return-gate.py: these
# hooks are global and take effect immediately, while the gate script other pods run is the
# released copy and would not carry the fix until promotion.
if not regs:
    print("UNSCOPED")
    sys.exit(0)

# (c) liveness — over REGISTERED workstreams, never over the repository.
for reg in regs:
    beat = reg["heartbeat"]
    seconds = age(beat)
    # A RANGE, not just an upper bound. JSON permits NaN and Python parses it, and every
    # comparison against NaN is False — so `seconds > WINDOW` was False and a heartbeat of NaN
    # passed liveness. A far-future stamp gives a large negative age and passed the same way.
    # Fail-closed means the age must be a finite number inside an explicit window.
    if seconds is None or seconds != seconds or seconds > WINDOW or seconds < -SKEW:
        print("BLOCK PLAN-SUPERVISOR: %s is registered but its supervisor is not running "
              "(no heartbeat since %s) — start it, or run plan-supervisor.py --unregister "
              "--slug %s to lift the requirement."
              % (reg["slug"], "never" if beat is None else beat, reg["slug"]))
        sys.exit(0)
print("OK")
PY
)"
if [ $? -ne 0 ] || [ -z "$VERDICT" ]; then
    printf 'PLAN-SUBAGENT-HOOK: the boundary and liveness step did not run — supervisor liveness is unverified.\n' >&2
    exit 2
fi

[ "$VERDICT" = "SKIP" ] && exit 0
# Nothing here is registered: not a plan session, so neither job (a) nor job (c) applies.
[ "$VERDICT" = "UNSCOPED" ] && exit 0

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

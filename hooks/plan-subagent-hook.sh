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
GATE="${HOOK_DIR%/hooks}/skills/plan/scripts/return-gate.py"

ROOT="${TMPDIR:-/tmp}/plan-subagent-$$"
mkdir -p "$ROOT" || exit 0
trap 'rm -rf "$ROOT"' EXIT
PAYLOAD="$ROOT/payload.json"
cat > "$PAYLOAD"

# Jobs (b) and (c). One line on stdout: SKIP, OK, or "BLOCK <message>".
VERDICT="$(python3 - "$PAYLOAD" <<'PY'
import json
import os
import sys
import time
from datetime import datetime

WINDOW = 120.0          # SPEC.md § 4.3a, seconds


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
    state = os.path.join(home, ".plan-guard", "state", "%s.json" % slug)
    try:
        with open(state, encoding="utf-8") as fh:
            beat = json.load(fh).get("heartbeat")
    except (OSError, ValueError):
        beat = None
    seconds = age(beat)
    if seconds is None or seconds > WINDOW:
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
python3 "$GATE" --hook < "$PAYLOAD"
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

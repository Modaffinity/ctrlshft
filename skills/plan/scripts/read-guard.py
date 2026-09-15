#!/usr/bin/env python3
"""M1 — the orchestrator cannot hold what bloats it.

A `PreToolUse` hook, matcher `Read`. Payload on stdin; the deny object of SPEC.md § 3.1
on stdout, or nothing. **Exit 0 in both directions** — the decision travels in the object,
never in the exit code, and a hook that exits non-zero on a Read it means to ALLOW breaks
every read in the session.

It denies when all FOUR of § 3.1's conditions hold, and the conjunction is the design:

  1. the payload carries no `agent_id`. MEASURED (Claude Code 2.1.263's own field
     description): `agent_id` is present only inside a subagent, so its ABSENCE is the
     top-level session. No roster file, nothing for a model to maintain (R144). A key
     present but EMPTY is read as absent, deliberately: the spec's condition is "carries
     no agent_id", and of the two readings only this one fails toward staying armed —
     the other lets a null a serialiser wrote disarm the guard silently.
  2. `cwd` resolves inside a git repository holding at least one live `plans/*/STATE.md`
     — not under `plans/archive/` — whose FRONTMATTER carries `session: build` and does
     not carry `guard: off`.
  3. the resolved `file_path` is protected (§ 3.2).
  4. the path is not on the allowlist, which is checked FIRST and wins over both rules.

**Armed by default; only `guard: off` disarms it (R160).** There is no arming step, so
there is nothing to forget: a `STATE.md` that says nothing about the guard is guarded,
which is the safe direction. Disarming is one tracked line in `git diff`, which is also
R158's escape hatch for an interactive operator session in the same pod — it too carries
no `agent_id` and is also denied, a false positive named here rather than hidden.

R141, carried and not closed: `@file` references bypass tool calls entirely and so bypass
`PreToolUse`. Dispatch briefs name paths and never `@`-reference them, so the path is
unused rather than closed.

Two implementation choices that are not incidental:

  * the repository is found by walking up for `.git`, not by shelling out to
    `git rev-parse` — this fires on EVERY Read, and a subprocess per read is a tax on the
    whole session;
  * frontmatter is parsed as frontmatter, never grepped. A `STATE.md` whose ledger quotes
    the words `session: build` in prose is not a live build workstream.

Stdlib only, Python 3.9.
"""
import json
import os
import sys

LINE_CAP = 800
ALLOW_NAMES = frozenset((
    "STATE.md", "BRIEF.md", "INDEX.md", "README.md", "CLAUDE.md", "AGENTS.md"))
ALLOW_SUFFIX = "_SIMPLE.md"
CHUNK = 65536

DENY_REASON = ("plan read-guard: %s is protected for the orchestrator (%s). "
               "Name the path in a dispatch; a child stage reads it.")


def repo_root(cwd):
    """The nearest ancestor of `cwd` holding a `.git` entry — a directory in an ordinary
    clone, a file in a worktree or submodule. None when `cwd` is not in a repository."""
    path = os.path.realpath(cwd)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def frontmatter(path):
    """The leading `---` block as a dict, or an empty dict. Read as frontmatter: a file
    that does not OPEN with the fence has none, and the block ends at its closing fence,
    so nothing in the body can arm the guard."""
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
            return {}          # unterminated block: not frontmatter
    except (OSError, UnicodeError):
        return {}


def live_workstreams(root):
    """Directories of every live build workstream in `root`: a `plans/*/STATE.md` outside
    `plans/archive/` whose frontmatter says `session: build` without `guard: off`."""
    plans = os.path.join(root, "plans")
    try:
        names = sorted(os.listdir(plans))
    except OSError:
        return []
    out = []
    for name in names:
        if name == "archive":
            continue
        d = os.path.join(plans, name)
        state = os.path.join(d, "STATE.md")
        if not os.path.isfile(state):
            continue
        meta = frontmatter(state)
        if meta.get("session") == "build" and meta.get("guard") != "off":
            out.append(d)
    return out


def allowlisted(path):
    name = os.path.basename(path)
    return name in ALLOW_NAMES or name.endswith(ALLOW_SUFFIX)


def line_count(path):
    """Lines in a text file, or None when it is absent, unreadable or binary. A file the
    guard cannot count is not protected BY THE COUNT — the pattern rule still applies."""
    try:
        with open(path, "rb") as fh:
            first = fh.read(CHUNK)
            if b"\x00" in first:
                return None
            n = first.count(b"\n")
            last = first
            while True:
                chunk = fh.read(CHUNK)
                if not chunk:
                    break
                n += chunk.count(b"\n")
                last = chunk
            if last and not last.endswith(b"\n"):
                n += 1
            return n
    except (OSError, ValueError):
        return None


def protected(path, workstreams):
    """The reason this path is protected, or None. § 3.2's two rules, in order — a spec
    is named by the pattern it matches even when it is also long."""
    name = os.path.basename(path)
    if os.path.dirname(path) in workstreams:
        if name == "SPEC.md":
            return "matches plans/*/SPEC.md"
        if name.endswith("-PLAN.md"):
            return "matches plans/*/*-PLAN.md"
    n = line_count(path)
    if n is not None and n > LINE_CAP:
        return "%d lines, over %d" % (n, LINE_CAP)
    return None


def decide(payload):
    """The deny object, or None. Every branch here is one of § 3.1's four conditions."""
    if payload.get("agent_id"):                                 # 1
        return None
    cwd = payload.get("cwd")
    raw = (payload.get("tool_input") or {}).get("file_path")
    if not cwd or not raw:
        return None
    root = repo_root(cwd)
    if root is None:
        return None
    workstreams = live_workstreams(root)                        # 2
    if not workstreams:
        return None
    path = os.path.realpath(os.path.join(cwd, os.path.expanduser(raw)))
    if allowlisted(path):                                       # 4, checked first
        return None
    reason = protected(path, workstreams)                       # 3
    if reason is None:
        return None
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": DENY_REASON % (path, reason)}}


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    decision = decide(payload)
    if decision is not None:
        sys.stdout.write(json.dumps(decision, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

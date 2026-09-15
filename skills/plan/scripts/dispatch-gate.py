#!/usr/bin/env python3
"""M10b — the executor, because "the first line of B6" is not one (SPEC.md § 12.1, X3).

A `PreToolUse` hook, matcher `Agent`. Payload on stdin; a deny object on stdout, or
nothing. **Exit 0 in both directions** — the decision travels in the object, never in the
exit code, and a hook that exits non-zero on a dispatch it means to ALLOW breaks every
dispatch in the session.

The draft called `b6-gate.sh` the first line of B6 and named nothing that runs it. A gate
whose executor is *the stage remembering to run it first* is an instruction, and C12
forbids those. **What makes B6 happen is a dispatch**, so that is where the gate binds.

It denies when BOTH hold, and the conjunction is the design:

  1. `tool_input.prompt` carries a line matching `^TASK: T[0-9]+` — the shipped form of a
     B6 task brief (SPEC.md § 17.6). MEASURED at B3 from Claude Code 2.1.263: `prompt`
     and `subagent_type` are the Agent tool's own parameters and the harness's own hook
     documentation describes a `PreToolUse` hook branching on `tool_input.subagent_type`,
     so `tool_input.*` is readable from this event.
  2. the live plan's `approved:` is not an ISO date — **asked of `b6-gate.sh`, never
     re-parsed here.** One parser, one refusal string: its stdout IS the
     `permissionDecisionReason`, so the CLI and the hook cannot drift into two answers.

Everything else prints nothing. B1–B5, and every non-plan dispatch on this machine, are
untouched — that is the point of testing the prompt before touching the filesystem.

Three resolution decisions:

  * **The plan is resolved by § 6.2's glob, through `return-gate.py` itself** rather than
    by a second copy of it, so "refusing ambiguity the same way" is true mechanically and
    not by inspection. Two live workstreams in one pod is a lawful state; silently
    picking one gates the dispatch on the wrong approval, so ambiguity DENIES.
  * **No live plan is not an ambiguity.** A repository with nothing to approve, or a cwd
    outside any repository, leaves the dispatch alone: there is no approval to read, and
    denying there would reach every `TASK:`-shaped dispatch on the machine.
  * **A gate that cannot answer denies.** `b6-gate.sh` exiting anything but 0 or 1 is a
    broken install, not an approval; the reason names the exit code. The module's own
    breakage is the one failure that stays open — the shim exits 0 and the traceback is
    on stderr — because a hook that cannot load must not take every dispatch down with
    it. Residual, carried (§ 12.1): a B6 task dispatched without a `TASK:` line evades
    this gate and runs into § 6.2 rule 4's rejection on the way back — two nets, neither
    a model complying.

Stdlib only, Python 3.9.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
GATE = os.path.join(HERE, "b6-gate.sh")
RETURN_GATE = os.path.join(HERE, "return-gate.py")

TASK_RE = re.compile(r"(?m)^TASK: T[0-9]+")
AMBIGUOUS = ("dispatch-gate: ambiguous plan (%d matches) — which workstream approves "
             "this dispatch is not guessed. B6 does not open.")
BROKEN = "dispatch-gate: b6-gate.sh did not run (exit %d) — B6 does not open."


def plan_resolver():
    """`return-gate.py`'s own glob resolution, loaded by path because the file is not an
    importable module name. Lazy: a dispatch with no `TASK:` line never pays for it."""
    spec = importlib.util.spec_from_file_location("plan_return_gate", RETURN_GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def deny(reason):
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}


def decide(payload):
    """The deny object, or None."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    prompt = tool_input.get("prompt")
    if not isinstance(prompt, str) or not TASK_RE.search(prompt):   # 1
        return None

    resolver = plan_resolver()
    root = resolver.repo_root(payload.get("cwd") or os.getcwd())
    if root is None:
        return None
    try:
        plan = resolver.resolve_plan(root)
    except resolver.Ambiguous as exc:
        return None if exc.n == 0 else deny(AMBIGUOUS % exc.n)

    result = subprocess.run(["bash", GATE, plan], capture_output=True, text=True)  # 2
    if result.returncode == 0:
        return None
    if result.returncode == 1:
        return deny(result.stdout.strip())
    sys.stderr.write(result.stderr)
    return deny(BROKEN % result.returncode)


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

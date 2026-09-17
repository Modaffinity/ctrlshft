#!/usr/bin/env python3
"""Run every gate the build session depends on, BEFORE the session starts.

The failure this closes, measured on release 4's B2 (2026-09-16): three of the spine's
own checks were broken, and all three surfaced mid-run — one of them by reporting a
correct 849-line spec as `0 of 0 constraints covered`, which under the between-stages
loop's `blocked` branch would have deleted it. None of these gates runs except during a
build session, so a fault in one is discovered by the run it breaks.

    preflight.py [--pod <path>] [--slug <slug>]

Read-only, except for its own scratch under `$TMPDIR`. It writes nothing into the pod,
`~/dotfiles` or `~/.claude`, so running it costs nothing and can be repeated.

**Every check states what it returns when the thing IS there** (`CHECKS.md` rule 1), and
the two that lean on a parser carry a positive control in the opposite direction: a gate
that accepted everything would pass a one-sided check while protecting nothing.

Exit: 0 all checks pass · 1 at least one FAIL · 2 usage (no pod, no live workstream).

Stdlib only, Python 3.9.
"""
import argparse
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
GUARD = os.path.join(HOME, ".claude", "plan-guard", "state")

VALID_RETURN = ("ARTIFACT: plans/x/SPEC.md\n"
                "LINES: 12\n"
                "VERDICT: done\n"
                "\n"
                "FINDINGS:\n"
                "- [advisory] nothing\n")
INVALID_RETURN = "I finished the spec and it looks good.\n"


def load(name):
    """Import a shipped script by filename. A hyphenated name is not importable, and a
    second copy of its logic is how two gates come to disagree about one file."""
    path = os.path.join(HERE, name)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_")[:-3], path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repo_root(path):
    path = os.path.realpath(path)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def frontmatter(path):
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


def live_slugs(pod):
    out = []
    for state in sorted(glob.glob(os.path.join(pod, "plans", "*", "STATE.md"))):
        if frontmatter(state).get("session") == "build":
            out.append(os.path.basename(os.path.dirname(state)))
    return out


def run(argv, stdin=None, env=None):
    merged = dict(os.environ)
    merged.update(env or {})
    return subprocess.run(argv, input=stdin, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True, env=merged)


class Report(object):
    """One line per check. `detail` says what was actually observed, never 'ok'."""

    def __init__(self):
        self.rows = []

    def add(self, ok, name, detail):
        self.rows.append((ok, name, detail))
        sys.stdout.write("%-5s %-22s %s\n" % ("PASS" if ok else "FAIL", name, detail))
        return ok

    def failed(self):
        return [r for r in self.rows if not r[0]]


def check_brief_readable(report, pod, slug):
    """The gate that broke: `coverage-pass.py` reported `0 of 0` on an approved brief
    because it matched one heading depth. What it returns when the brief IS readable is
    a non-empty key list, so that is what this asserts — and the control asserts the
    same parser still returns nothing for a brief with no Constraint headings, which is
    what makes the first half mean something."""
    brief = os.path.join(pod, "plans", slug, "BRIEF.md")
    if not os.path.isfile(brief):
        return report.add(False, "brief-readable", "no BRIEF.md at %s" % brief)
    cover = load("coverage-pass.py")
    with open(brief, encoding="utf-8", errors="replace") as fh:
        keys = cover.brief_keys(fh.read())
    control = cover.brief_keys("# B\n\n## Constraints\n\n**C1** not a heading\n")
    if control:
        return report.add(False, "brief-readable",
                          "control failed: a brief with no Constraint heading parsed as "
                          "%d keys — the parser is matching something else" % len(control))
    if not keys:
        return report.add(False, "brief-readable",
                          "0 constraints parsed from %s — the BRIEF is unreadable to the "
                          "Coverage pass; every stage gated on it will blame the artifact"
                          % os.path.relpath(brief, pod))
    return report.add(True, "brief-readable",
                      "%d constraints parsed (%s … %s); control returned 0"
                      % (len(keys), keys[0], keys[-1]))


def check_coverage_pass(report, pod, slug):
    """Informational when the spec exists: the Coverage pass must be able to RUN here,
    whatever it finds. Exit 2 means it could not read the brief and is a FAIL; exit 1
    means it read both and found uncovered rows, which is B3's business, not preflight's."""
    base = os.path.join(pod, "plans", slug)
    brief, spec = os.path.join(base, "BRIEF.md"), os.path.join(base, "SPEC.md")
    if not os.path.isfile(spec):
        return report.add(True, "coverage-pass", "no SPEC.md yet — nothing to score")
    res = run([sys.executable, os.path.join(HERE, "coverage-pass.py"), brief, spec,
               "--kind", "spec"])
    line = next((l for l in res.stdout.splitlines() if l.startswith("COVERAGE:")),
                "<no COVERAGE line>")
    if res.returncode == 2:
        return report.add(False, "coverage-pass", "exit 2 — %s" % line)
    return report.add(True, "coverage-pass", "exit %d — %s" % (res.returncode, line))


def check_return_gate(report):
    """The gate that was blind: `return-gate.py --hook` read the last assistant TEXT,
    while a subagent's report travels in a `SubagentHandback` tool call. Both directions
    are asserted against the same construct — a reader that returned OK for anything
    would pass the first assertion and protect nothing."""
    root = tempfile.mkdtemp(prefix="preflight-rg-")
    try:
        pod = os.path.join(root, "pod")
        os.makedirs(os.path.join(pod, ".git"))
        for name, text in (("good.jsonl", VALID_RETURN), ("bad.jsonl", INVALID_RETURN)):
            rows = [json.dumps({"type": "assistant", "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Writing the return."}]}}),
                    json.dumps({"type": "assistant", "message": {
                        "role": "assistant",
                        "content": [{"type": "tool_use", "name": "SubagentHandback",
                                     "input": {"message": text}}]}})]
            with open(os.path.join(root, name), "w", encoding="utf-8") as fh:
                fh.write("\n".join(rows) + "\n")
        results = {}
        for name in ("good.jsonl", "bad.jsonl"):
            payload = json.dumps({"session_id": "preflight", "cwd": pod,
                                  "transcript_path": os.path.join(root, name),
                                  "hook_event_name": "SubagentStop"})
            res = run([sys.executable, os.path.join(HERE, "return-gate.py"), "--hook"],
                      stdin=payload, env={"HOME": os.path.join(root, "home")})
            results[name] = (res.returncode, res.stderr.strip())
        good, bad = results["good.jsonl"], results["bad.jsonl"]
        if good[0] != 0:
            return report.add(False, "return-gate",
                              "a VALID return handed back by tool call was rejected: %s "
                              "— every stage verdict this session reads is unread" % good[1])
        if bad[0] == 0:
            return report.add(False, "return-gate",
                              "control failed: a return with no VERDICT line was ACCEPTED")
        return report.add(True, "return-gate",
                          "hand-back read: valid passed, invalid rejected (%s)" % bad[1])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def check_guard_writable(report):
    """The supervisor's state directory. `~/.claude` is denied writes by the sandbox —
    correctly, it holds settings and hooks — and the supervisor's own scratch sits inside
    it, so it dies on start. What this returns when the thing IS there is a created and
    removed probe file."""
    probe = os.path.join(GUARD, ".preflight-probe")
    try:
        os.makedirs(GUARD, exist_ok=True)
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("probe\n")
        os.remove(probe)
    except OSError as exc:
        return report.add(False, "supervisor-state",
                          "%s is not writable (%s) — launch plan-supervisor.py outside "
                          "the command sandbox, or move the guard root" % (GUARD, exc.strerror))
    return report.add(True, "supervisor-state", "%s writable (probe created, removed)" % GUARD)


def check_hook_wiring(report, pod):
    """Every hook the spine depends on, live in BOTH settings files with the right
    matcher and command — `check-hook-wiring.py`'s own criterion, invoked exactly as
    release 3's AC20-w2 invokes it."""
    script = os.path.join(HERE, "check-hook-wiring.py")
    inventory = os.path.join(HERE, "hook-inventory.json")
    settings = os.path.join(HOME, "dotfiles", ".claude", "settings.json")
    mirror = os.path.join(HOME, "dotfiles", "hooks", "settings-hooks.json")
    for path in (script, inventory, settings, mirror):
        if not os.path.isfile(path):
            return report.add(False, "hook-wiring", "%s is missing" % path)
    res = run([sys.executable, script, "--expect", inventory, "--settings", settings,
               "--mirror", mirror, "--pod", pod])
    lines = (res.stdout or res.stderr).strip().splitlines()
    return report.add(res.returncode == 0, "hook-wiring",
                      "exit %d — %s" % (res.returncode,
                                        lines[-1] if lines else "no output"))


def check_state(report, pod, slug):
    """`STATE.md` is what a fresh session resumes from, so a preflight reads it the way
    that session will: the frontmatter must name a stage and a verdict, and the artifact
    the last ledger block claims must exist AND be tracked. What this returns when the
    thing IS there is the claimed stage and the file it points at."""
    state = os.path.join(pod, "plans", slug, "STATE.md")
    meta = frontmatter(state)
    if not meta.get("stage") or not meta.get("verdict"):
        return report.add(False, "state-resumable",
                          "%s has no stage/verdict frontmatter — a fresh session cannot "
                          "place itself" % os.path.relpath(state, pod))
    claimed = []
    with open(state, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.lstrip().startswith("- **Artifact:**"):
                # The FIRST link on the line is the stage's artifact; anything after it
                # is an also-changed path, and checking that one instead would report a
                # stage's artifact as present when only its side effect is.
                hit = re.search(r"\(([^()]+\.md)\)", line)
                if hit:
                    claimed.append(hit.group(1))
    last = claimed[-1] if claimed else None
    if last is None:
        return report.add(True, "state-resumable",
                          "stage %s / %s; no artifact claimed yet"
                          % (meta["stage"], meta["verdict"]))
    resolved = os.path.normpath(os.path.join(pod, "plans", slug, last))
    if not os.path.isfile(resolved):
        return report.add(False, "state-resumable",
                          "the last ledger block claims %s, which is not on disk" % last)
    res = run(["git", "-C", pod, "ls-files", "--error-unmatch",
               os.path.relpath(resolved, pod)])
    if res.returncode != 0:
        return report.add(False, "state-resumable",
                          "%s exists but is UNTRACKED — Resume reads that as absent and "
                          "deletes it" % last)
    return report.add(True, "state-resumable",
                      "stage %s / %s; last artifact %s exists and is tracked"
                      % (meta["stage"], meta["verdict"], last))


def check_codex(report):
    """The second-model seat has died mid-run in two consecutive releases. The vehicle is
    the official plugin; what this returns when it IS there is the resolved binary path."""
    binary = os.environ.get("CODEX_BIN") or shutil.which("codex")
    if not binary:
        return report.add(False, "codex-seat",
                          "no `codex` on PATH and CODEX_BIN unset — every review round "
                          "stops on its vehicle")
    return report.add(True, "codex-seat", binary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pod", default=None, help="default: the repository holding cwd")
    parser.add_argument("--slug", default=None, help="default: the live build workstream")
    args = parser.parse_args(argv)

    pod = args.pod or repo_root(os.getcwd())
    if not pod or not os.path.isdir(pod):
        sys.stderr.write("preflight: cwd is not in a repository; pass --pod.\n")
        return 2
    slugs = [args.slug] if args.slug else live_slugs(pod)
    if not slugs:
        sys.stderr.write("preflight: no live build workstream under %s/plans; pass "
                         "--slug.\n" % pod)
        return 2
    if len(slugs) > 1:
        sys.stderr.write("preflight: %d live workstreams (%s) — name one with --slug.\n"
                         % (len(slugs), ", ".join(slugs)))
        return 2
    slug = slugs[0]

    print("preflight: %s · %s\n" % (os.path.basename(pod), slug))
    report = Report()
    check_brief_readable(report, pod, slug)
    check_coverage_pass(report, pod, slug)
    check_return_gate(report)
    check_guard_writable(report)
    check_hook_wiring(report, pod)
    check_state(report, pod, slug)
    check_codex(report)

    bad = report.failed()
    print("\n%d checks, %d failed" % (len(report.rows), len(bad)))
    if bad:
        print("Fix these before the build session; each line above says what was observed.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

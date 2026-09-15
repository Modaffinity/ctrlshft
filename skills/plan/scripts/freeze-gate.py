#!/usr/bin/env python3
"""Freeze gate — an artifact cannot be recorded frozen unless it earned it.

  freeze-gate.py --artifact <path> --brief <path> --kind spec|plan|brief
  freeze-gate.py --kind spec --dial-only <path>     # prints the stripped dial count

`brief` is in the kind enum because C15 covers all three workstream artifacts, and
the companion's name is never derived by string surgery — `<slug>-PLAN.md` derives
the wrong one — but read from a fixed map, resolved in the artifact's own directory.

THE GATE RUNS COVERAGE ITSELF. It never reads a claimed `COVERAGE:` line, because a
line can be written without the pass running, and that is release 2's fourth failure
row exactly. Re-running a script is free: when a rewrite changes the artifact,
Coverage runs again at freeze, so `frozen` implies `executed`.

Checks, in order, first failure wins:

  | Check       | Keys | Kinds       | Rejects when                                  |
  | Coverage    | C6   | spec, plan  | coverage-pass.py exits non-zero               |
  | Companion   | C15  | all three   | the mapped companion is absent, or > 75 lines |
  | Dial        | C19  | spec, plan  | not exactly one stripped `**Dial:**` line     |
  | Batch       | C8   | plan        | no `batch` column, or any cell empty          |
  | Route       | C14  | plan        | no `route` column, or any cell empty          |
  | Comparable  | C17  | plan        | no `comparable` column, or any cell empty     |
  | Prediction  | C17  | plan        | the predictor did not run (structural test)   |

Two of these were broken in the draft and both are RESCOPED, never waived:

  * Dial. The unstripped sweep returns 2 on a correct spec, because the spec ships
    the dial TEMPLATE inside a fence. The exemption is CHECKS.md rule 2's own — a
    marker inside a fence is a mention, not an instance — and it is named in code by
    importing `strip_code` from docs-graph-check.py, never taken as a run-time
    argument. An argument leaves no record and has to be re-decided every run.
  * Prediction. Requiring only that a `## Predicted spend` HEADING exist is
    satisfied by an empty section. It now checks the predictor ran: one table row
    per task row, a `Total:` line, and a `Matched <n> of <n> tasks` line whose first
    number is greater than zero.

Exit: 0 pass · 1 rejected, one line naming the check and the artifact · 2 the gate
could not run (a missing file, an unreadable brief) — never confused with a reject.

Stdlib only, Python 3.9.
"""
import argparse
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COVERAGE = os.path.join(HERE, "coverage-pass.py")
COMPANION_CAP = 75

# C15 covers all three artifacts. The map is fixed, because the plan's own name is
# `<slug>-PLAN.md` and string surgery on it derives `<slug>-PLAN_SIMPLE.md`.
COMPANION = {"brief": "BRIEF_SIMPLE.md",
             "spec": "SPEC_SIMPLE.md",
             "plan": "PLAN_SIMPLE.md"}

DIAL = re.compile(r"^\*\*Dial:\*\*")
TOTAL = re.compile(r"^Total:\s*\$[\d,.]+,\s*\d+\s*min,\s*over\s*\d+\s*dispatches\.")
MATCHED = re.compile(r"\bMatched\s+(\d+)\s+of\s+(\d+)\s+tasks\b")
PREDICTED_HEADING = re.compile(r"^##\s+Predicted spend\s*$")
TOP_HEADING = re.compile(r"^##\s+\S")


def load_strip_code():
    path = os.path.join(HERE, "docs-graph-check.py")
    spec = importlib.util.spec_from_file_location("docs_graph_check", path)
    if spec is None or spec.loader is None:
        raise SystemExit("freeze-gate: cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.strip_code


strip_code = load_strip_code()


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def defenced(text):
    """Fenced blocks and inline code spans removed, via the shipped exemption."""
    return strip_code(text).splitlines()


def split_row(line):
    body = line.strip()
    if not body.startswith("|"):
        return None
    return [c.strip() for c in body.strip("|").split("|")]


def is_rule_row(cells):
    return all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells)


def task_table(lines):
    """(header, data rows) of the plan's task table, or (None, []). Identified by its
    header naming both `task` and `acceptance` — never by position, because the
    column set is what this gate is checking."""
    for i, line in enumerate(lines):
        cells = split_row(line)
        if not cells:
            continue
        header = [c.lower() for c in cells]
        if "task" in header and "acceptance" in header:
            rows, j = [], i + 1
            while j < len(lines):
                row = split_row(lines[j])
                if row is None:
                    break
                if not is_rule_row(row):
                    rows.append(row)
                j += 1
            return header, rows
    return None, []


def predicted_rows(lines):
    """Data rows of the first table under `## Predicted spend`."""
    for i, line in enumerate(lines):
        if not PREDICTED_HEADING.match(line):
            continue
        rows, j, in_table = [], i + 1, False
        while j < len(lines):
            if TOP_HEADING.match(lines[j]):
                break
            row = split_row(lines[j])
            if row is not None:
                in_table = True
                if not is_rule_row(row) and not (
                        [c.lower() for c in row][:1] == ["task"]):
                    rows.append(row)
            elif in_table and lines[j].strip() == "":
                pass
            j += 1
        return rows
    return None


def reject(check, artifact, detail):
    print("freeze-gate: %s — %s (%s)" % (check, detail, artifact))
    return 1


def check_coverage(artifact, brief, kind):
    if kind not in ("spec", "plan"):
        return 0
    if not os.path.isfile(COVERAGE):
        print("freeze-gate: coverage cannot run — %s is missing" % COVERAGE,
              file=sys.stderr)
        return 2
    run = subprocess.run([sys.executable, COVERAGE, brief, artifact, "--kind", kind],
                         capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)
    if run.returncode != 0:
        return reject("coverage failed", artifact,
                      "coverage-pass.py exited %d" % run.returncode)
    return 0


def check_companion(artifact, kind):
    name = COMPANION[kind]
    path = os.path.join(os.path.dirname(os.path.abspath(artifact)), name)
    if not os.path.isfile(path):
        return reject("companion missing", artifact,
                      "%s is not beside the artifact" % name)
    count = len(read(path).splitlines())
    if count > COMPANION_CAP:
        return reject("companion over cap", artifact,
                      "%s is %d lines, cap %d" % (name, count, COMPANION_CAP))
    print("freeze-gate: companion ok — %s, %d lines (cap %d)" % (name, count, COMPANION_CAP))
    return 0


def dial_count(lines):
    return sum(1 for line in lines if DIAL.match(line))


def check_dial(artifact, lines, kind):
    if kind not in ("spec", "plan"):
        return 0
    count = dial_count(lines)
    if count != 1:
        return reject("dial line count %d, expected exactly 1" % count, artifact,
                      "the sweep strips fenced blocks and inline code spans first")
    print("freeze-gate: dial ok — 1 line (stripped sweep)")
    return 0


def check_column(artifact, header, rows, name):
    if header is None:
        return reject("%s column" % name, artifact, "the artifact has no task table")
    if name not in header:
        return reject("%s column missing" % name, artifact,
                      "the task table's columns are: %s" % ", ".join(header))
    idx = header.index(name)
    for row in rows:
        ident = row[0] if row else "?"
        if idx >= len(row) or not row[idx]:
            return reject("%s cell empty" % name, artifact,
                          "task row %s carries no %s value" % (ident, name))
    print("freeze-gate: %s column ok — %d task row(s)" % (name, len(rows)))
    return 0


def check_prediction(artifact, lines, rows):
    pred = predicted_rows(lines)
    if pred is None:
        return reject("prediction missing", artifact,
                      "no `## Predicted spend` section — a heading alone is not the "
                      "predictor having run")
    if len(pred) != len(rows):
        return reject("prediction row count", artifact,
                      "%d predicted row(s) against %d task row(s)" % (len(pred), len(rows)))
    text = "\n".join(lines)
    if not any(TOTAL.match(line.strip()) for line in lines):
        return reject("prediction total missing", artifact,
                      "no `Total: $<n>, <n> min, over <n> dispatches.` line")
    hit = MATCHED.search(text)
    if hit is None:
        return reject("prediction match line missing", artifact,
                      "no `Matched <n> of <n> tasks` line")
    if int(hit.group(1)) == 0:
        return reject("prediction matched nothing", artifact,
                      "`Matched 0 of %s tasks` — every task unmatched produces a "
                      "plausible zero and is a failure, not a cheap plan" % hit.group(2))
    print("freeze-gate: prediction ok — %d row(s), matched %s of %s"
          % (len(pred), hit.group(1), hit.group(2)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifact")
    ap.add_argument("--brief")
    ap.add_argument("--kind", choices=tuple(COMPANION), required=True)
    ap.add_argument("--dial-only", metavar="PATH",
                    help="print the stripped `**Dial:**` line count of PATH and stop")
    args = ap.parse_args()

    if args.dial_only:
        if not os.path.isfile(args.dial_only):
            print("freeze-gate: no such file: %s" % args.dial_only, file=sys.stderr)
            return 2
        print(dial_count(defenced(read(args.dial_only))))
        return 0

    if not args.artifact or not args.brief:
        ap.error("--artifact and --brief are required unless --dial-only is given")
    for path in (args.artifact, args.brief):
        if not os.path.isfile(path):
            print("freeze-gate: no such file: %s" % path, file=sys.stderr)
            return 2

    lines = defenced(read(args.artifact))

    rc = check_coverage(args.artifact, args.brief, args.kind)
    if rc:
        return rc
    rc = check_companion(args.artifact, args.kind)
    if rc:
        return rc
    rc = check_dial(args.artifact, lines, args.kind)
    if rc:
        return rc

    if args.kind == "plan":
        header, rows = task_table(lines)
        for name in ("batch", "route", "comparable"):
            rc = check_column(args.artifact, header, rows, name)
            if rc:
                return rc
        rc = check_prediction(args.artifact, lines, rows)
        if rc:
            return rc

    print("freeze-gate: ok — %s (%s)" % (args.artifact, args.kind))
    return 0


if __name__ == "__main__":
    sys.exit(main())

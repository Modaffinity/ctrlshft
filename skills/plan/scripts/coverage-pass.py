#!/usr/bin/env python3
"""Coverage pass — does the artifact point at every Constraint the brief carries.

  coverage-pass.py <brief> <artifact> [--kind spec|plan]

Replaces the dispatched judgement-pass at exactly the point where it was being
skipped (release 2's fourth failure row: specified-reviewed-frozen-skipped). The
judgement half of review — does section N actually satisfy C<n> — stays with the
review cycle; what becomes mechanical is that the pass EXECUTED against the bytes
being frozen, which is why the last line is the artifact's sha256.

Two parsing rules are load-bearing and both were measured, not reasoned:

  * The brief's `## Constraints` section is the requirement list and nothing else.
    `Research used` and `Decisions settled` are provenance and demand nothing.
  * The artifact's canonical key table is read AS A TABLE, never by grepping a key:
    `C1` is a prefix of `C11`, so `grep -c 'C1'` returns 1 against a line naming
    only C11. (The commonly given reason — that `\\b` differs between BSD and GNU
    grep — is false; the prefix hazard alone carries the rule.)

Fenced blocks are stripped from both documents before anything is counted, via
`strip_code` imported from docs-graph-check.py — the shipped exemption mechanism
(CHECKS.md rule 2: a marker inside a fence is a mention, not an instance). A
template table quoted in a spec is not that spec's key table.

Exit: 0 clean · 1 any UNCOVERED row or any cited heading absent · 2 the empty case
(a brief whose Constraints section did not parse yields `COVERAGE: 0 of 0`, which
is blocked, never a pass).

Stdlib only, Python 3.9.
"""
import argparse
import hashlib
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

CONSTRAINTS_HEADING = re.compile(r"^##\s+Constraints\s*$")
TOP_HEADING = re.compile(r"^##\s+\S")
KEY_HEADING = re.compile(r"^####\s+(C\d+)\b")
# `## 3. C1 — ...`, `### 4.3a Liveness ...`, `### 7.1 The Coverage script`.
SECTION_HEADING = re.compile(r"^(#{2,3})\s+(\d+(?:\.\d+)*[a-z]?)(?=[.:)\s]|$)")
SECTION_CITE = re.compile(r"§\s*(\d+(?:\.\d+)*[a-z]?)")
OK_STATUS = ("covered", "ruled")


def load_strip_code():
    """Import the shipped exemption rather than re-implementing it. Re-implementing
    it is how two gates come to disagree about one file."""
    path = os.path.join(HERE, "docs-graph-check.py")
    spec = importlib.util.spec_from_file_location("docs_graph_check", path)
    if spec is None or spec.loader is None:
        raise SystemExit("coverage-pass: cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.strip_code


strip_code = load_strip_code()


def read(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    return raw, raw.decode("utf-8", errors="replace")


def defenced(text):
    """Lines of `text` with fenced blocks and inline code spans removed, via the
    shipped exemption. A table or a heading quoted as a template is a mention, not an
    instance — CHECKS.md rule 2, and the reason `grep -c '^## '` over a reference
    counted headings inside a fence."""
    return strip_code(text).splitlines()


def brief_keys(brief_text):
    """Every `#### C<n> — ...` heading inside `## Constraints`, in the order found."""
    keys, inside = [], False
    for line in defenced(brief_text):
        if CONSTRAINTS_HEADING.match(line):
            inside = True
            continue
        if inside and TOP_HEADING.match(line):
            break
        if inside:
            hit = KEY_HEADING.match(line)
            if hit and hit.group(1) not in keys:
                keys.append(hit.group(1))
    return keys


def split_row(line):
    body = line.strip()
    if not body.startswith("|"):
        return None
    cells = [c.strip() for c in body.strip("|").split("|")]
    return cells


def is_rule_row(cells):
    return all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells)


def key_tables(artifact_lines):
    """Every table whose header names key/status/where, as lists of data rows."""
    tables, i, n = [], 0, len(artifact_lines)
    while i < n:
        cells = split_row(artifact_lines[i])
        header = [c.lower() for c in cells] if cells else []
        if len(header) >= 3 and header[0] == "key" and header[1] == "status" \
                and header[2] == "where":
            rows, j = [], i + 1
            while j < n:
                row = split_row(artifact_lines[j])
                if row is None:
                    break
                if not is_rule_row(row):
                    rows.append(row)
                j += 1
            tables.append(rows)
            i = j
            continue
        i += 1
    return tables


def artifact_sections(artifact_lines):
    """The leading number of every `##`/`###` heading. A row's `§ <n>` resolves iff
    some heading begins with that same number — the rule the key table is read against."""
    return set(SECTION_HEADING.match(l).group(2)
               for l in artifact_lines if SECTION_HEADING.match(l))


def task_table_sections(artifact_lines):
    """Every `§ <n>` named by a row of the plan's task table. At --kind plan a
    Constraint is satisfied when at least one task names the section its row points
    at — spec-kit's `requirements with zero associated tasks`."""
    found, seen_table, i, n = set(), False, 0, len(artifact_lines)
    while i < n:
        cells = split_row(artifact_lines[i])
        header = [c.lower() for c in cells] if cells else []
        if "task" in header and "acceptance" in header:
            seen_table = True
            j = i + 1
            while j < n:
                row = split_row(artifact_lines[j])
                if row is None:
                    break
                if not is_rule_row(row):
                    for cell in row:
                        found.update(SECTION_CITE.findall(cell))
                j += 1
            i = j
            continue
        i += 1
    return seen_table, found


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brief")
    ap.add_argument("artifact")
    ap.add_argument("--kind", choices=("spec", "plan"), default="spec")
    args = ap.parse_args()

    for path in (args.brief, args.artifact):
        if not os.path.isfile(path):
            print("coverage-pass: no such file: %s" % path, file=sys.stderr)
            return 2

    _, brief_text = read(args.brief)
    raw, artifact_text = read(args.artifact)
    digest = hashlib.sha256(raw).hexdigest()
    lines = defenced(artifact_text)

    keys = brief_keys(brief_text)
    print("ARTIFACT: %s" % args.artifact)
    if not keys:
        print("COVERAGE: 0 of 0 constraints covered")
        print()
        print("sha256: %s" % digest)
        print()
        print("FINDINGS:")
        print("- [blocking] the `## Constraints` section of %s did not parse — "
              "0 of 0 is blocked, never a pass" % args.brief)
        return 2

    findings = []
    tables = key_tables(lines)
    if len(tables) > 1:
        findings.append("[blocking] %s carries %d canonical key tables; there is "
                        "exactly one" % (args.artifact, len(tables)))
    rows = {}
    for table in tables:
        for cells in table:
            key = cells[0]
            if not re.fullmatch(r"C\d+", key or ""):
                continue
            if key in rows:
                findings.append("[blocking] %s has more than one row for %s"
                                % (args.artifact, key))
                continue
            rows[key] = cells

    sections = artifact_sections(lines)
    if args.kind == "plan":
        seen_task_table, task_sections = task_table_sections(lines)
        if not seen_task_table:
            findings.append("[blocking] %s has no task table, so no row's section "
                            "can be named by a task" % args.artifact)
    else:
        seen_task_table, task_sections = True, None

    report, covered = [], 0
    for key in keys:
        cells = rows.pop(key, None)
        if cells is None:
            report.append((key, "UNCOVERED", "—"))
            findings.append("[blocking] %s is UNCOVERED — no row for it in the key "
                            "table of %s" % (key, args.artifact))
            continue
        status = (cells[1] if len(cells) > 1 else "").lower()
        where = cells[2] if len(cells) > 2 else ""
        if status not in OK_STATUS:
            report.append((key, "UNCOVERED", where or "—"))
            findings.append("[blocking] %s has status %r — the three statuses are "
                            "covered, ruled, UNCOVERED" % (key, cells[1] if len(cells) > 1 else ""))
            continue
        cited = SECTION_CITE.findall(where)
        if not cited:
            report.append((key, "UNCOVERED", where or "—"))
            findings.append("[blocking] %s cites no section — a `covered` or `ruled` "
                            "row names the heading that satisfies it" % key)
            continue
        absent = [c for c in cited if c not in sections]
        if absent:
            report.append((key, "UNCOVERED", where))
            findings.append("[blocking] %s cites § %s, and no `##` or `###` heading "
                            "of %s begins with that number"
                            % (key, ", § ".join(absent), args.artifact))
            continue
        if args.kind == "plan" and seen_task_table:
            unnamed = [c for c in cited if c not in task_sections]
            if unnamed:
                report.append((key, "UNCOVERED", where))
                findings.append("[blocking] %s cites § %s, which no task's "
                                "requirements name in %s"
                                % (key, ", § ".join(unnamed), args.artifact))
                continue
        report.append((key, status, where))
        covered += 1

    for stale in sorted(rows):
        report.append((stale, "STALE", rows[stale][2] if len(rows[stale]) > 2 else "—"))
        findings.append("[blocking] %s has a row for %s, which the brief's "
                        "Constraints section does not carry" % (args.artifact, stale))

    print("COVERAGE: %d of %d constraints covered" % (covered, len(keys)))
    print()
    print("| key | status | where |")
    print("|---|---|---|")
    for key, status, where in report:
        print("| %s | %s | %s |" % (key, status, where or "—"))
    print()
    print("sha256: %s" % digest)
    if findings:
        print()
        print("FINDINGS:")
        for finding in findings:
            print("- " + finding)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

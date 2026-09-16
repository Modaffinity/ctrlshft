#!/usr/bin/env python3
"""Check a documentation tree: reachability, broken references, size, trackedness, serves:.

Five checks in one pass. Exit 0 when clean, 1 when any finding is printed. Every line is
`<kind>: <path>: <detail>`; `exempt:` lines are reports, not findings, and never set the
exit code. Checks 1 and 3 run over the candidate set (every non-excluded *.md under --root);
checks 4 and 5 run over the reached set. Stdlib only; Python 3.9 compatible.

Guidance for the docs stage that runs this: references/DOCS_STAGE.md.
"""
import argparse
import fnmatch
import os
import re
import subprocess
import sys
from collections import deque

# A name belongs here only because the pod's .gitignore deliberately keeps that directory out.
EXCLUDED = (".git", ".claude", ".superpowers", "node_modules", "__pycache__",
            "outputs", "evidence", "inputs", "subprojects")

MAX_DEPTH = 4

# A file that is appended to by contract cannot live under a line cap: the documentation
# stage's item 5 appends one entry to RUN_REPORT.md every run. Matched by BASENAME.
SIZE_EXEMPT = ("RUN_REPORT.md",)

# A workstream's own BRIEF/SPEC/PLAN/STATE/DOCS is a third document kind: its length is a
# function of the work it records, not of how readable it is as doctrine (spec ruling R15).
# Matched by RELATIVE PATH, one glob segment at a time.
SIZE_EXEMPT_GLOB = ("plans/*/*.md", "plans/archive/*/*.md",
                    "plans/*/notes/*.md", "plans/archive/*/notes/*.md")

FM_SERVES = re.compile(r"^serves:\s*\S", re.M)

FENCE = re.compile(r"^\s*(```|~~~)")
# [^`\n]*, never [^`]*: the wider form lets one stray unpaired backtick pair with the
# opening backtick of a real code span lines below it and delete every link between
# them, which turns a reached document into a phantom `orphan`.
INLINE_CODE = re.compile(r"`[^`\n]*`")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def is_excluded(rel):
    """True when a directory segment of `rel` is excluded. `.venv*` is a prefix match.
    `subprojects` excludes anything with a directory below it, never subprojects/CLAUDE.md."""
    parts = rel.split(os.sep)
    for i, part in enumerate(parts[:-1]):
        if part.startswith(".venv"):
            return True
        if part == "subprojects":
            if i + 1 <= len(parts) - 2:
                return True
            continue
        if part in EXCLUDED:
            return True
    return False


def strip_code(text):
    """Drop fenced blocks, then inline code spans. A document that quotes link syntax
    otherwise yields phantom targets."""
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        out.append("" if in_fence else line)
    return INLINE_CODE.sub("", "\n".join(out))


def links_in(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    return MD_LINK.findall(strip_code(text))


def is_local(target):
    return not target.startswith("#") and not SCHEME.match(target)


def candidates(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in EXCLUDED and not d.startswith(".venv")]
        for name in filenames:
            if not name.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            if not is_excluded(rel):
                found.append(rel)
    return sorted(found)


def walk(root, start):
    """Breadth-first from `start` over markdown links. Returns (depth, findings, reached)."""
    findings = []
    depth = {start: 0}
    reached = [start]
    queue = deque([start])
    while queue:
        rel = queue.popleft()
        if not rel.endswith(".md"):
            continue
        here = os.path.join(root, rel)
        for raw in links_in(here):
            target = raw.split("#", 1)[0]
            if not target or not is_local(target):
                continue
            expanded = os.path.expanduser(target)
            if os.path.isabs(expanded):
                resolved = os.path.normpath(expanded)
            else:
                resolved = os.path.normpath(os.path.join(os.path.dirname(here), expanded))
            if not os.path.exists(resolved):
                findings.append(("missing", rel, "link target does not exist: " + raw))
                continue
            tgt = os.path.relpath(resolved, root)
            if tgt.startswith(".."):
                continue          # outside the tree; it exists, so it is not missing
            if is_excluded(tgt):
                continue          # exists, so not missing; never walked, sized or checked
            if tgt in depth:
                continue
            depth[tgt] = depth[rel] + 1
            if depth[tgt] > MAX_DEPTH:
                findings.append(("too-deep", tgt,
                                 "first reached at depth %d (max %d)" % (depth[tgt], MAX_DEPTH)))
            reached.append(tgt)
            queue.append(tgt)
    return depth, findings, reached


def tracked_set(root):
    proc = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("error: git ls-files failed in %s: %s" % (root, proc.stderr.strip()))
    return set(proc.stdout.splitlines())


def check_orphans(cands, reached, start):
    seen = set(reached)
    return [("orphan", rel, "not reachable from " + start) for rel in cands if rel not in seen]


def check_tracked(root, reached, tracked):
    out = []
    for rel in reached:
        if os.path.isdir(os.path.join(root, rel)):
            continue
        if rel not in tracked:
            out.append(("untracked", rel, "reached but not in git ls-files"))
    return out


def line_count(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return sum(1 for _ in fh)


def glob_match(rel, pattern):
    """fnmatch one path segment at a time, so `*` never crosses a separator. Bare
    fnmatch would let `plans/*/*.md` swallow `plans/a/notes/b.md`."""
    parts = rel.split(os.sep)
    pats = pattern.split("/")
    if len(parts) != len(pats):
        return False
    return all(fnmatch.fnmatchcase(p, q) for p, q in zip(parts, pats))


def size_budget(rel, profile, start):
    if profile == "package":
        return 300 if rel == start else 500
    base = os.path.basename(rel)
    if base == "ARCHITECTURE.md":
        return 300
    if base == "CONTEXT.md":
        # A glossary grows by one entry every time a release names something, so it is the one
        # root document whose length is a function of how much work the pod has done rather than
        # of how well it is written. Raised from the 200-line root budget on 2026-09-16, when
        # plan v4's grill added three terms and landed it at exactly 200 of 200.
        return 300
    if os.sep not in rel:            # any root-level .md, README.md included
        return 200
    if base == "INDEX.md":           # any */INDEX.md
        return 200
    return 500


def check_size(root, cands, profile, start):
    findings, exempt = [], []
    for rel in cands:
        try:
            count = line_count(os.path.join(root, rel))
        except OSError:
            continue
        if os.path.basename(rel) in SIZE_EXEMPT:
            exempt.append(("exempt", rel,
                           "%d lines; size check skipped (appended to by contract)" % count))
            continue
        if any(glob_match(rel, pat) for pat in SIZE_EXEMPT_GLOB):
            exempt.append(("exempt", rel,
                           "%d lines; size check skipped (workstream artifact)" % count))
            continue
        budget = size_budget(rel, profile, start)
        if count > budget:
            findings.append(("oversize", rel, "%d lines (budget %d)" % (count, budget)))
    return findings, exempt


def has_serves(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            if fh.readline().strip() != "---":
                return False
            block = []
            for line in fh:
                if line.strip() == "---":
                    break
                block.append(line)
    except OSError:
        return False
    return bool(FM_SERVES.search("".join(block)))


def check_serves(root, reached, profile):
    """Check 5 runs under --profile pod only: a skill package's files carry the skill's
    frontmatter, not a pod document's."""
    if profile != "pod":
        return []
    out = []
    for rel in reached:
        path = os.path.join(root, rel)
        if not rel.endswith(".md") or os.path.isdir(path):
            continue
        if not has_serves(path):
            out.append(("no-serves", rel, "frontmatter has no serves: field"))
    return out


def git_top_level():
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("error: not inside a git repository and --root was not given")
    return proc.stdout.strip()


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=None, help="tree to check (default: the git top level)")
    parser.add_argument("--start", default="README.md", help="reachability root (default: README.md)")
    parser.add_argument("--profile", choices=("pod", "package"), default="pod")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = os.path.abspath(args.root) if args.root else git_top_level()
    if not os.path.exists(os.path.join(root, args.start)):
        print("missing: %s: reachability root does not exist" % args.start)
        return 1
    tracked = tracked_set(root)
    cands = candidates(root)
    _, findings, reached = walk(root, args.start)
    findings += check_orphans(cands, reached, args.start)
    findings += check_tracked(root, reached, tracked)
    size_findings, exempt = check_size(root, cands, args.profile, args.start)
    findings += size_findings
    findings += check_serves(root, reached, args.profile)
    for kind, path, detail in sorted(exempt):
        print("%s: %s: %s" % (kind, path, detail))
    for kind, path, detail in sorted(findings):
        print("%s: %s: %s" % (kind, path, detail))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

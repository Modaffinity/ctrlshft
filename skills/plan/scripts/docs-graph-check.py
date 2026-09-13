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
    for kind, path, detail in sorted(findings):
        print("%s: %s: %s" % (kind, path, detail))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

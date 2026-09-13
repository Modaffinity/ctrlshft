#!/usr/bin/env python3
"""Assemble an advisor packet: the artifact, the brief, one level of dependency closure,
and the level below that. Copies every file into one flat directory and writes MANIFEST.md
with each file's source path and sha256.

Usage: advisor-packet.py <artifact> --brief <path> --out <dir> [--root <pod root>]

Stdlib only; Python 3.9 compatible. The rule set is references/REVIEW_ROUNDS.md.
"""
import argparse
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
from collections import namedtuple

BASENAME_MATCH_LIMIT = 3
PACKET_EXCLUDED = (".claude", ".superpowers", "evidence", "outputs", "inputs",
                   "node_modules", "subprojects")
DOTFILES = os.path.expanduser("~/dotfiles")
DOTCLAUDE = os.path.expanduser("~/.claude")

RULE_TIER = {1: "B", 2: "B", 5: "B", 3: "C", 4: "C", 6: "C", 7: "C", 8: "C"}
Dep = namedtuple("Dep", "src rule tier")

FENCE = re.compile(r"^\s*(```|~~~)")
# [^`\n]+, never [^`]+: the wider form reaches from the first backtick of an opening fence
# to the first backtick of the closing one and swallows the block, which hides whether
# defence() is doing anything at all.
SPAN = re.compile(r"`([^`\n]+)`")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
AT_REF = re.compile(r"(?:^|\s)@([~./][^\s,;)]+)")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
FM_PATH_KEYS = ("brief", "research", "sources", "spec", "plan")
SH_SOURCE = re.compile(r"^\s*(?:source|\.)\s+(\S+)", re.M)
SH_PATHISH = re.compile(r"(?<![\w/])((?:~|\.{1,2})?/[\w./~-]+\.(?:md|py|sh|json|ya?ml|txt))")
PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.M)
PY_STRING = re.compile(r"['\"]([^'\"\n]*\.(?:md|py|sh|json|ya?ml|txt))['\"]")
BASENAME = re.compile(r"^[A-Za-z0-9][\w.-]*\.(?:md|py|sh|json|ya?ml|txt)$")
SKILLNAME = re.compile(r"^[a-z][a-z0-9-]*$")
BRACES = re.compile(r"\{([^{}]+)\}")


def superpowers_skills_root():
    matches = sorted(glob.glob(os.path.join(
        DOTCLAUDE, "plugins", "cache", "*", "superpowers", "*", "skills")))
    return matches[-1] if matches else None


def skill_roots():
    roots = [os.path.join(DOTFILES, "skills"), os.path.join(DOTCLAUDE, "skills")]
    sp = superpowers_skills_root()
    if sp:
        roots.append(sp)
    return roots


def defence(text):
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def spans(text):
    return SPAN.findall(defence(text))


def prose(text):
    return SPAN.sub("", defence(text))


def md_links(text):
    return [t.split("#", 1)[0] for t in MD_LINK.findall(text)
            if not t.startswith("#") and not SCHEME.match(t)]


def at_refs(text):
    return AT_REF.findall(text)


def frontmatter_paths(raw):
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    out = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() not in FM_PATH_KEYS:
            continue
        value = value.strip().strip("[]")
        for part in value.split(","):
            part = part.strip().strip("'\"")
            # a URL in a `sources:` list is not a path: without this filter every one
            # reaches resolve(), fails its SCHEME guard and becomes an `unresolved:`
            # note — the flooding rule 4's silence exists to prevent, reproduced here.
            if part and not SCHEME.match(part):
                out.append(part)
    return out


def shell_deps(raw):
    return SH_SOURCE.findall(raw) + SH_PATHISH.findall(raw)


def python_imports(raw):
    """Rule 4's first half. A module name becomes the candidate `<module>.py`; the caller
    resolves it against the repo and DROPS what does not resolve, without a note, because
    `import os` is not an unresolved dependency — it is the standard library."""
    return [m.split(".")[0] + ".py" for m in PY_IMPORT.findall(raw)]


def python_strings(raw):
    return PY_STRING.findall(raw)


def expand_braces(text):
    match = BRACES.search(text)
    if not match:
        return [text]
    out = []
    for option in match.group(1).split(","):
        out += expand_braces(text[:match.start()] + option.strip() + text[match.end():])
    return out


def resolve(base_dir, target):
    """Absolute REAL path, or None. realpath, never abspath: on macOS /tmp and /var are
    symlinks, so two spellings of one file would otherwise become two packet members and
    a pod file named by an unresolved absolute path would look out-of-reach."""
    if not target or SCHEME.match(target):
        return None
    path = os.path.expanduser(target)
    path = path if os.path.isabs(path) else os.path.join(base_dir, path)
    path = os.path.normpath(path)
    return os.path.realpath(path) if os.path.exists(path) else None


def line_of(raw, needle):
    for number, line in enumerate(raw.splitlines(), 1):
        if needle in line:
            return number
    return 0


def _excluded_rel(rel):
    return any(seg in PACKET_EXCLUDED for seg in rel.split(os.sep)[:-1])


def basename_matches(name, root, tracked):
    return [os.path.join(root, rel) for rel in tracked
            if os.path.basename(rel) == name and not _excluded_rel(rel)]


def dir_children(path, suffixes):
    return sorted(os.path.join(path, n) for n in os.listdir(path)
                  if n.endswith(suffixes) and os.path.isfile(os.path.join(path, n)))


def deps_of(path, root, tracked):
    """Return (deps, unresolved, ambiguous) for one file. Paths in `deps` are absolute."""
    deps, unresolved, ambiguous = [], [], []
    base_dir = os.path.dirname(os.path.abspath(path))
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError:
        return deps, unresolved, ambiguous

    namer = os.path.relpath(os.path.abspath(path), root)
    if namer.startswith(".."):
        namer = os.path.basename(path)

    def add(target, rule, base=None, note_unresolved=True):
        got = resolve(base or base_dir, target)
        if got is None:
            if note_unresolved:
                # the spec's form, with the line: a note naming only a basename cannot be
                # followed back to the sentence that made the claim.
                unresolved.append("unresolved: %s (named by %s:%d)"
                                  % (target, namer, line_of(raw, target)))
            return
        if os.path.isdir(got):
            if rule == 5:
                for child in dir_children(got, (".md",)):
                    deps.append(Dep(os.path.realpath(child), rule, RULE_TIER[rule]))
            elif rule == 7:
                for child in dir_children(got, (".md", ".py", ".sh")):
                    deps.append(Dep(os.path.realpath(child), rule, RULE_TIER[rule]))
            return
        deps.append(Dep(got, rule, RULE_TIER[rule]))

    if path.endswith(".sh"):
        for target in shell_deps(raw):
            add(target, 3)
        return deps, unresolved, ambiguous
    if path.endswith(".py"):
        for target in python_imports(raw):
            add(target, 4, note_unresolved=False)
        for target in python_strings(raw):
            add(target, 4)
        return deps, unresolved, ambiguous

    text = prose(raw)
    for target in md_links(text):
        add(target, 1)
    for target in at_refs(text):
        add(target, 2)
    for target in frontmatter_paths(raw):
        # A frontmatter path value is pod-root-relative by convention — `brief:` and
        # `research:` are written that way — which is how `research: [research/<topic>/]`
        # reaches its README and five documents. Fall back to the containing directory.
        add(target, 5, root if resolve(root, target) else None)
    for span in spans(raw):
        span = span.strip()
        if BASENAME.match(span):
            hits = basename_matches(span, root, tracked)
            if len(hits) > BASENAME_MATCH_LIMIT:
                ambiguous.append("ambiguous-basename: %s (%d matches)" % (span, len(hits)))
            else:
                for hit in hits:
                    deps.append(Dep(os.path.realpath(hit), 6, RULE_TIER[6]))
        elif span.startswith("~/dotfiles/") or span.startswith(DOTFILES + "/"):
            for option in expand_braces(span):
                add(option, 7)
        elif SKILLNAME.match(span):
            for sroot in skill_roots():
                candidate = os.path.join(sroot, span, "SKILL.md")
                if os.path.exists(candidate):
                    deps.append(Dep(os.path.realpath(candidate), 8, RULE_TIER[8]))
                    break
    return deps, unresolved, ambiguous

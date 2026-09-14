#!/usr/bin/env python3
"""Assemble an advisor packet: the artifact, the brief, one level of dependency closure,
and the level below that. Copies every file into one flat directory and writes MANIFEST.md
with each file's source path and sha256.

Usage: advisor-packet.py <artifact> --brief <path> --out <dir> [--root <pod root>]

Stdlib only; Python 3.9 compatible. The rule set is references/REVIEW_ROUNDS.md.
"""
import argparse
import datetime
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
# Directory names under ~/dotfiles that never enter a packet. Resolved against DOTFILES
# at call time, never written as an absolute home path. Add a name here, not a new rule.
NEVER_PACKET = ("secrets",)

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


def never_packet(path):
    """True for a NEVER_PACKET directory or anything inside it. Rule 7 reads a backticked
    `~/dotfiles/...` span as a dependency, and release 1's VERIFICATION.md backticks
    `~/dotfiles/secrets` in a sentence explaining that the sandbox denies reading it —
    which is exactly what made the assembler try to read it. A packet goes to `ask-codex`,
    a third-party model: the `.env` files never matched the copied suffixes, but a
    `README.md` documenting the layout would have. Tested before any listing, so the
    protection is this rule and not the sandbox that happened to refuse first."""
    for name in NEVER_PACKET:
        base = os.path.realpath(os.path.join(DOTFILES, name))
        if path == base or path.startswith(base + os.sep):
            return True
    return False


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
        if never_packet(got):
            # loud, never silent: a file dropped without a note is the failure the
            # packet's own rules exist to prevent. Before the isdir branch, because a
            # backticked `~/dotfiles/secrets/setup.sh` is a FILE and never lists anything.
            unresolved.append("excluded: %s (named by %s:%d, never copied into a packet)"
                              % (got, namer, line_of(raw, target)))
            return
        if os.path.isdir(got):
            suffixes = {5: (".md",), 7: (".md", ".py", ".sh")}.get(rule)
            if suffixes is None:
                return
            try:
                children = dir_children(got, suffixes)
            except OSError:
                # a directory this process cannot list contributes nothing and must not
                # be fatal: one PermissionError on `~/dotfiles/secrets` propagated out of
                # main() and killed the whole assembly, manifest included.
                unresolved.append("unreadable: %s (named by %s:%d, not copied)"
                                  % (got, namer, line_of(raw, target)))
                return
            for child in children:
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


CAP_FILES = 50
CAP_BYTES = 500 * 1024
TIER_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


def packet_name(src, root):
    # realpath, never abspath: on macOS /tmp and /var are symlinks, and a process's
    # cwd is already resolved while a path handed in on the command line is not, so
    # abspath alone makes a pod file look like an out-of-tree one.
    src = os.path.realpath(src)
    sp = superpowers_skills_root()
    for prefix, base in (("superpowers", sp and os.path.realpath(sp)),
                         ("dotfiles", os.path.realpath(DOTFILES)),
                         ("dotclaude", os.path.realpath(DOTCLAUDE)),
                         ("pod", os.path.realpath(root))):
        if base and (src == base or src.startswith(base + os.sep)):
            rel = os.path.relpath(src, base)
            break
    else:
        prefix, rel = "ext", src.lstrip(os.sep)
    parts = rel.split(os.sep)
    if parts[-1].startswith("."):
        parts[-1] = parts[-1][1:] + ".txt"
    return prefix + "--" + "--".join(parts)


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_files(root):
    proc = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("error: git ls-files failed in %s: %s" % (root, proc.stderr.strip()))
    return proc.stdout.splitlines()


def _assign(tiers, path, tier):
    if path not in tiers or TIER_ORDER[tier] < TIER_ORDER[tiers[path]]:
        tiers[path] = tier


def closure(artifact, brief, root, tracked):
    tiers, dependents, notes = {}, {}, []
    artifact = os.path.realpath(artifact)
    brief = os.path.realpath(brief)
    _assign(tiers, artifact, "A")
    _assign(tiers, brief, "A")
    level1 = []
    for parent in (artifact, brief):
        deps, unresolved, ambiguous = deps_of(parent, root, tracked)
        notes += unresolved + ambiguous
        for dep in deps:
            # distinct parents, never mentions: the tier rule drops by how many packet
            # FILES depend on a file, and a spec that names `PLAN.md` fifteen times
            # would otherwise outrank a skill ten different files import.
            dependents.setdefault(dep.src, set()).add(parent)
            if dep.src in (artifact, brief):
                continue
            _assign(tiers, dep.src, dep.tier)
            level1.append(dep.src)
    for parent in sorted(set(level1)):
        deps, unresolved, ambiguous = deps_of(parent, root, tracked)
        notes += unresolved + ambiguous
        for dep in deps:
            dependents.setdefault(dep.src, set()).add(parent)
            _assign(tiers, dep.src, "D")
    reachable = tuple(os.path.realpath(base) + os.sep
                      for base in (root, DOTFILES, DOTCLAUDE))
    evicted = [p for p in sorted(tiers)
               if tiers[p] != "A" and not p.startswith(reachable)]
    for path in evicted:
        # recorded AND removed: the spec says an out-of-reach dependency is not copied,
        # so leaving it in the tiers would put it in the packet with a note beside it.
        notes.append("out-of-reach: %s (not copied)" % path)
        del tiers[path]
    return tiers, dependents, notes


def drop_to_cap(tiers, dependents):
    kept = sorted(tiers, key=lambda p: (TIER_ORDER[tiers[p]], p))
    dropped = []

    def total_bytes(paths):
        return sum(os.path.getsize(p) for p in paths if os.path.exists(p))

    while len(kept) > CAP_FILES or total_bytes(kept) > CAP_BYTES:
        droppable = [p for p in kept if tiers[p] != "A"]
        if not droppable:
            return kept, dropped
        worst_tier = max(TIER_ORDER[tiers[p]] for p in droppable)
        pool = [p for p in droppable if TIER_ORDER[tiers[p]] == worst_tier]
        pool.sort(key=lambda p: (len(dependents.get(p, ())), -os.path.getsize(p)))
        victim = pool[0]
        kept.remove(victim)
        dropped.append((victim, tiers[victim], len(dependents.get(victim, ()))))
    return kept, dropped


def write_manifest(out_dir, artifact, brief, rows, notes, dropped, cap_exceeded):
    total = sum(size for _, _, _, size in rows)
    # Frontmatter, not decoration: docs-graph-check.py's check 5 requires a leading `---`
    # block carrying `serves:`, and a manifest is committed. Without this every packet
    # adds a `no-serves:` finding the operator hand-patches away (ruling R88).
    lines = ["---", "serves: both", "type: reference",
             "updated: %s" % datetime.date.today().isoformat(), "---", "",
             "# Packet manifest — %s" % os.path.basename(artifact), "",
             "Assembled by `advisor-packet.py` from %s, brief %s." % (artifact, brief),
             "**%d files, %d KB** against the %d-file / %d KB cap."
             % (len(rows), total // 1024, CAP_FILES, CAP_BYTES // 1024), "",
             "| Flattened name | Source path | Tier | sha256 |", "|---|---|---|---|"]
    for name, src, tier, _ in rows:
        lines.append("| `%s` | `%s` | %s | `%s` |" % (name, src, tier, sha256_of(src)))
    lines += ["", "## Notes", ""]
    entries, seen = [], set()          # dedupe: one note per distinct fact, not per mention
    for note in notes:
        if note not in seen:
            seen.add(note)
            entries.append(note)
    entries += ["dropped: %s (tier %s, %d dependents)" % d for d in dropped]
    if cap_exceeded:
        entries.append("cap-exceeded")
    for entry in entries or ["none"]:
        lines.append("- " + entry)
    with open(os.path.join(out_dir, "MANIFEST.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("artifact")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", default=None,
                        help="pod root for rule 6's basename search (default: git top level)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = os.path.realpath(args.root) if args.root else os.path.realpath(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip())
    for path in (args.artifact, args.brief):
        if not os.path.exists(path):
            print("error: does not exist: %s" % path, file=sys.stderr)
            return 1
    tracked = tracked_files(root)
    tiers, dependents, notes = closure(args.artifact, args.brief, root, tracked)
    kept, dropped = drop_to_cap(tiers, dependents)
    # the flag means the packet is not what the brief promised: one level of closure,
    # whole. A tier D drop is level 2 and by design; a tier B or C drop is level 1 and
    # is the failure. Measuring it over tier A bytes alone made it unreachable in
    # practice — a 192-file closure cut to 21 raised nothing.
    kept_bytes = sum(os.path.getsize(p) for p in kept if os.path.exists(p))
    cap_exceeded = (any(tier != "D" for _, tier, _ in dropped)
                    or len(kept) > CAP_FILES or kept_bytes > CAP_BYTES)
    out_dir = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for src in kept:
        name = packet_name(src, root)
        shutil.copy2(src, os.path.join(out_dir, name))
        rows.append((name, src, tiers[src], os.path.getsize(src)))
    rows.sort()
    write_manifest(out_dir, os.path.abspath(args.artifact), os.path.abspath(args.brief),
                   rows, notes, dropped, cap_exceeded)
    print("%d files, %d KB -> %s" % (len(rows), sum(r[3] for r in rows) // 1024, out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())

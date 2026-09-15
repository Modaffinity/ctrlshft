#!/usr/bin/env python3
"""M15 -- resume-check.py: proves the C4 resume claim against a real STATE.md ledger.

Two runs. `--emit-expect` snapshots a STATE.md BEFORE a handoff transition into a small
JSON expectation file: the next pending stage id, the block-count and artifact list of
every already-`done` stage (what must NOT gain a new block), and the list of still-pending
stage ids (what must NOT turn `done` without a real artifact). After the transition, the
comparison run re-parses STATE.md and reports two findings:

  * REDONE  -- a stage id that was already `done` now owns MORE ledger blocks than it did
    before the transition. This is deliberately NOT "this header text appears twice": a
    real STATE.md gives one stage id (`B3`, `B5`) four legitimate ledger blocks for a
    four-step review cycle, all present before the transition -- that is not a redo.
  * SKIPPED -- a stage id that was still pending is now `done`, and at least one artifact
    path its new ledger block(s) claim does not exist on disk, or exists but is not
    tracked by git. `Artifact: none` makes no claim and is never flagged.

Both are read from disk, never recalled: `git log --oneline <since>..HEAD` in `--repo` is
the commit evidence, `STATE.md`'s ledger blocks and `## The stages` summary table are the
ledger evidence (SPEC.md § 5, requirement 3).

Scope note, recorded here rather than guessed at: an artifact is only checked when the
`**Artifact:**` bullet carries a markdown link (`[label](path)`). A small minority of
ledger blocks (the `(not a stage)` wave summaries) describe several files in prose with no
link at all -- those are outside what this script can check mechanically and are not
flagged either way. This is a scope decision, not a silent gap: it is named in T11's task
return as an advisory finding.

Exit codes: 0 both tables empty · 1 either table has a row · 2 the expectation file is
absent or did not parse (or the git/repo setup needed to run the comparison is unusable) --
`blocked`, never a zero/zero pass (CHECKS.md rule 1).

Stdlib only, Python 3.9.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

STAGE_ID_RE = re.compile(r'^[A-Za-z]+\d+$')
HEADER_ID_RE = re.compile(r'^(?:Stage|Wave)\s+(\S+)')
LINK_RE = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
STAGES_TABLE_RE = re.compile(r'^## The stages\n(.*?)(?:\n## |\Z)', re.S | re.M)
LEDGER_SECTION_RE = re.compile(r'^## Stage ledger\n(.*)\Z', re.S | re.M)
ARTIFACT_BULLET_RE = re.compile(r'^- \*\*Artifact:\*\*(.*?)(?=\n- \*\*|\Z)', re.S | re.M)


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def sha256_of(path):
    return hashlib.sha256(read_text(path).encode("utf-8")).hexdigest()


def parse_stage_table(text):
    """Ordered (id, verdict) pairs from `## The stages`. Rows whose id cell is not a
    letter-run + digits token (`W0`, `B6`, ...) are excluded on purpose -- the C16 gate
    row's id cell is a bare em dash, not a stage id."""
    m = STAGES_TABLE_RE.search(text)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 4:
            continue
        rid, verdict = cells[0], cells[-1]
        if not STAGE_ID_RE.match(rid):
            continue
        rows.append((rid, verdict.strip('*').strip().lower()))
    return rows


def parse_ledger_blocks(text, base_dir):
    """One dict per `### ` block: {sid, verdict, artifact_paths} in ledger order. `sid` is
    None for a block whose header does not start `Stage <id>` / `Wave <id>` (an
    `Interstage` block, say) -- those never appear in the summary table and are never
    tracked as a stage id. `verdict` is None when the header carries no verdict segment,
    which the real file does for every `Interstage` header."""
    m = LEDGER_SECTION_RE.search(text)
    if not m:
        return []
    section = m.group(1)
    parts = re.split(r'(?m)^### ', section)[1:]
    blocks = []
    for part in parts:
        header_line, _, body = part.partition('\n')
        segments = [s.strip() for s in header_line.split('·')]
        name = segments[0]
        verdict = segments[1].lower() if len(segments) >= 3 else None
        sid_match = HEADER_ID_RE.match(name)
        sid = sid_match.group(1) if sid_match else None
        artifact_paths = []
        am = ARTIFACT_BULLET_RE.search(body)
        if am:
            for link in LINK_RE.findall(am.group(1)):
                if link.startswith(("http://", "https://")):
                    continue
                artifact_paths.append(os.path.normpath(os.path.join(base_dir, link)))
        blocks.append({"sid": sid, "verdict": verdict, "artifact_paths": artifact_paths})
    return blocks


def snapshot(state_path):
    text = read_text(state_path)
    base_dir = os.path.dirname(os.path.abspath(state_path))
    return parse_stage_table(text), parse_ledger_blocks(text, base_dir)


def block_counts(blocks):
    counts = {}
    for b in blocks:
        if b["sid"]:
            counts[b["sid"]] = counts.get(b["sid"], 0) + 1
    return counts


def emit_expect(state_path, expect_path):
    table, blocks = snapshot(state_path)
    counts = block_counts(blocks)
    artifacts = {}
    for b in blocks:
        if not b["sid"]:
            continue
        bucket = artifacts.setdefault(b["sid"], [])
        for p in b["artifact_paths"]:
            rel = os.path.relpath(p, os.path.dirname(os.path.abspath(state_path)))
            if rel not in bucket:
                bucket.append(rel)
    done_ids = [rid for rid, v in table if v == "done"]
    pending_ids = [rid for rid, v in table if v != "done"]
    payload = {
        "next_stage": pending_ids[0] if pending_ids else None,
        "pending_stages": pending_ids,
        "done_stages": {
            rid: {"block_count": counts.get(rid, 0), "artifacts": artifacts.get(rid, [])}
            for rid in done_ids
        },
    }
    with open(expect_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def is_tracked(repo, rel_path):
    res = subprocess.run(["git", "-C", repo, "ls-files", "--error-unmatch", rel_path],
                         capture_output=True, text=True)
    return res.returncode == 0


def compare(state_path, expect_path, since, repo):
    try:
        with open(expect_path, encoding="utf-8") as fh:
            expect = json.load(fh)
    except FileNotFoundError:
        print("RESUME-CHECK: blocked -- expectation file %s is absent" % expect_path)
        return 2
    except (json.JSONDecodeError, OSError, ValueError):
        print("RESUME-CHECK: blocked -- expectation file %s did not parse" % expect_path)
        return 2
    if not isinstance(expect, dict) or not {"done_stages", "pending_stages"} <= set(expect):
        print("RESUME-CHECK: blocked -- expectation file %s did not parse" % expect_path)
        return 2

    log = subprocess.run(["git", "-C", repo, "log", "--oneline", "%s..HEAD" % since],
                         capture_output=True, text=True)
    if log.returncode != 0:
        print("RESUME-CHECK: blocked -- git log --oneline %s..HEAD failed in %s"
              % (since, repo))
        return 2
    commit_count = len([l for l in log.stdout.splitlines() if l.strip()])

    try:
        table, blocks = snapshot(state_path)
    except OSError:
        print("RESUME-CHECK: blocked -- state file %s is absent" % state_path)
        return 2

    counts_now = block_counts(blocks)
    verdict_now = dict(table)
    state_dir = os.path.dirname(os.path.abspath(state_path))

    redone_rows = []
    for sid, info in sorted(expect["done_stages"].items()):
        before = info.get("block_count", 0)
        now = counts_now.get(sid, 0)
        if now > before:
            redone_rows.append((sid, before, now))

    skipped_rows = []
    for sid in expect["pending_stages"]:
        if verdict_now.get(sid) != "done":
            continue
        paths = []
        for b in blocks:
            if b["sid"] == sid:
                paths.extend(b["artifact_paths"])
        if not paths:
            continue
        for p in paths:
            rel = os.path.relpath(p, os.path.abspath(repo))
            if not os.path.exists(p):
                skipped_rows.append((sid, rel, "missing on disk"))
            elif not is_tracked(repo, rel):
                skipped_rows.append((sid, rel, "untracked"))

    print("commits since %s: %d" % (since, commit_count))
    print("REDONE:")
    if redone_rows:
        for sid, before, now in redone_rows:
            print("  %s expected %d block(s), found %d" % (sid, before, now))
    else:
        print("  (none)")
    print("SKIPPED:")
    if skipped_rows:
        for sid, rel, reason in skipped_rows:
            print("  %s %s -- %s" % (sid, rel, reason))
    else:
        print("  (none)")
    print("RESUME-CHECK: %d redone, %d skipped" % (len(redone_rows), len(skipped_rows)))
    print("sha256: %s" % sha256_of(state_path))
    del state_dir
    return 1 if (redone_rows or skipped_rows) else 0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--state", required=True)
    p.add_argument("--expect", required=True)
    p.add_argument("--since")
    p.add_argument("--repo")
    p.add_argument("--emit-expect", action="store_true")
    args = p.parse_args(argv)

    if args.emit_expect:
        emit_expect(args.state, args.expect)
        return 0

    if not args.since or not args.repo:
        print("RESUME-CHECK: blocked -- --since and --repo are required for a comparison run")
        return 2
    return compare(args.state, args.expect, args.since, args.repo)


if __name__ == "__main__":
    sys.exit(main())

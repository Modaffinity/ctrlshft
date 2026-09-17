#!/usr/bin/env python3
"""M2 — an incomplete `done` is not accepted.

The measured failure: a stage returned `done` having verified 6 of 19 criteria, and two
of the thirteen it never mentioned were failing. Nothing read the return; the orchestrator
read the word `done`. This makes the reading mechanical.

**Two interfaces, both specified**, because a fresh subagent given one would invent the
other (`SPEC.md` § 6.1, TA8):

  * **File mode** — `--return <path> --plan <path>` — reads two named files and prints one
    `RETURN-GATE:` line on **stdout**. `--plan` takes the plan itself, or a directory to
    resolve the plan in by the glob below; the directory form is what makes the ambiguity
    branch runnable outside a live session.
  * **Hook mode** — `--hook`, payload on stdin — takes `transcript_path` from the payload,
    extracts the subagent's last RETURN — its last assistant text block, or the `message`
    of a `SubagentHandback` tool call, whichever comes last — locates the plan by the glob,
    and prints the same line on **stderr** so it reaches the subagent as the block reason.
    The handback form is not optional: MEASURED 2026-09-16, a subagent's report reaches its
    parent as `SubagentHandback(message=...)` and the transcript's last assistant TEXT at
    that moment is something else entirely, so a text-only reader rejects two valid returns
    for "no VERDICT line" and the stage's real verdict is never read at all.

Both exit `0` ok, `2` rejected. Nothing else exits non-zero, so a usage error is a usage
error and never reads as a clean return.

**Four validity rules** (§ 6.2), and the order they run in is not decorative — the size
cap short-circuits, because reasons computed over a return too large to be a return are
noise.

  1. *Shape* — a `VERDICT:` line reading `done`, `blocked` or `stop`; the OUTPUT keys the
     declared kind requires per `INTERFACES.md` § *Output kinds*; a `FINDINGS:` section.
  2. *Size cap* — 6,000 bytes (R146). This is C1's return path: an artifact must not be
     pastable back, and the longest legitimate return shape is under 2 KB.
  3. *Consistency* — `done` with an open `[blocking]` finding.
  4. *Completeness* — a `TASK: <id>` + `VERDICT: done` return carries one `CRITERIA:` row
     per criterion the plan gives that task, and is rejected on any shortfall, any row
     with no check command, any row whose recorded output is empty, and **any row whose
     verdict token is `[FAIL]` or absent**. **6 of 19 is rejected exactly as 0 of 19 is,
     and 19 of 19 with one `[FAIL]` is rejected too** — `BRIEF.md`'s C5 says *"missing,
     unevidenced, or failing"*, and a `done` return carrying a failed criterion is the
     exact shape release 2 shipped.

Five reading decisions that are not incidental:

  * **Row ids are matched verbatim** against the plan's identifiers, never by a numeric
    pattern: `AC9-size`, `AC36-parse`, `A11` and `AC20-w2` are all identifiers, and
    § 17.6's `AC<n>` placeholder would admit only the numeric ones (X1).
  * **The criteria block is bounded by its `CRITERIA:` header**, ending at the next
    `KEY:` line. `- [advisory] …` under `FINDINGS:` has the same leading shape as
    `- [AC1] …`; a parser that scans the whole return rejects every legitimate return in
    the estate.
  * **The separator is `→` or `->`.** § 17.6 ships the arrow; the returns this run
    actually made and accepted use the ASCII form. Accepting one would reject real work
    over a keyboard, which is CHECKS.md rule 2's shape. The split is at the FIRST
    separator, so a command containing `->` still yields a non-empty command and a
    non-empty output — which is all the two row rules ask.
  * **The declared kind is inferred from the OUTPUT keys present**, never demanded as a
    field: `ROUND:` declares `findings`, `MOVED:` `move`, and so on. No marker means no
    declared kind and the rule is vacuous — which is what makes a task return and a
    `blocked` return with `ARTIFACT: none` lawful.
  * **Ambiguity is refused, never guessed** (§ 6.2). Two live workstreams in one pod is a
    lawful state; silently picking one validates against the wrong criteria list.

Stdlib only, Python 3.9.
"""
import argparse
import glob
import json
import os
import re
import sys
import time

SIZE_CAP = 6000
VERDICTS = ("done", "blocked", "stop")
PLAN_GLOB = os.path.join("plans", "*", "[a-z]*-PLAN.md")
ARCHIVE = os.sep + os.path.join("plans", "archive") + os.sep
ARROWS = ("→", "->")

KEY_RE = re.compile(r"^([A-Z][A-Z ]*[A-Z]):")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
BULLET_RE = re.compile(r"^-\s+\*\*([^*]+)\*\*")
ROW_RE = re.compile(r"^-\s*\[([^\]]+)\]\s*(.*)$")
TOKEN_RE = re.compile(r"\[(PASS|FAIL)\]\s*$")
BLOCKING_RE = re.compile(r"(?m)^\s*-\s*\[blocking\]")

# (markers that declare this kind, its name, the keys it requires) — INTERFACES.md
# § *Output kinds*, in an order that reads the most specific marker first: a B7 `files`
# return also carries LINES, so `files` must be tested before `file`.
KINDS = (
    (("MOVED",), "move", ("MOVED",)),
    (("MERGE",), "merge", ("MERGE",)),
    (("ALSO CHANGED",), "files", ("ARTIFACT", "LINES", "ALSO CHANGED")),
    (("ROUND",), "findings", ("ARTIFACT", "ROUND")),
    (("BRANCH", "COMMITS", "TASKS"), "commits", ("BRANCH", "COMMITS", "TASKS")),
    (("LINES",), "file", ("ARTIFACT", "LINES")),
)


class Ambiguous(Exception):
    """The plan glob matched other than exactly one file. Its message is NOT a rejection
    reason — § 6.2 ships a line of its own — so it travels as an exception rather than
    joining the reason list."""

    def __init__(self, n):
        Exception.__init__(self, n)
        self.n = n


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def repo_root(cwd):
    """The nearest ancestor of `cwd` holding a `.git` entry, or None."""
    path = os.path.realpath(cwd)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def resolve_plan(root):
    """The one live plan under `root`, or Ambiguous. Archived workstreams are excluded by
    path, not by trusting the glob's shape."""
    matches = sorted(p for p in glob.glob(os.path.join(root, PLAN_GLOB))
                     if ARCHIVE not in p + os.sep)
    if len(matches) != 1:
        raise Ambiguous(len(matches))
    return matches[0]


def output_keys(text):
    """The OUTPUT keys a return declares — every `KEY:` at the start of a line."""
    return set(m.group(1) for m in (KEY_RE.match(l) for l in text.splitlines()) if m)


def declared_kind(keys):
    for markers, kind, required in KINDS:
        if keys.intersection(markers):
            return kind, required
    return None, ()


def criteria_rows(text):
    """The rows of the `CRITERIA:` block, as `(id, command, output, token)`.

    The block starts after the `CRITERIA:` header and ends at the next `KEY:` line, which
    is what keeps `FINDINGS:`' `- [advisory] …` bullets out of the criteria list."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("CRITERIA:"):
            start = i + 1
            break
    if start is None:
        return []
    rows = []
    for line in lines[start:]:
        if KEY_RE.match(line):
            break
        m = ROW_RE.match(line)
        if not m:
            continue
        rest = m.group(2).strip()
        token = TOKEN_RE.search(rest)
        if token:
            rest = rest[:token.start()].strip()
        command, output = rest, ""
        for arrow in ARROWS:
            at = rest.find(arrow)
            if at != -1:
                command = rest[:at].strip()
                output = rest[at + len(arrow):].strip()
                break
        rows.append((m.group(1).strip(), command, output,
                     token.group(1) if token else None))
    return rows


def task_criteria(plan_text, task_id):
    """The criterion ids the plan gives `task_id`, in plan order — the bullets under that
    task's `### Acceptance` heading whose first bold span is the identifier. None when the
    plan has no single section for the task; `[]` when it has one and it is empty."""
    lines = plan_text.splitlines()
    token = re.compile(r"(?<![0-9A-Za-z])(?:Task\s+)?%s(?![0-9A-Za-z])"
                       % re.escape(task_id))
    heads = []
    fenced = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEAD_RE.match(line)
        if m and token.search(m.group(2)):
            heads.append((i, len(m.group(1))))
    if len(heads) != 1:
        return None
    start, level = heads[0]

    end = len(lines)
    fenced = False
    for i in range(start + 1, len(lines)):
        if FENCE_RE.match(lines[i]):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEAD_RE.match(lines[i])
        if m and len(m.group(1)) <= level:
            end = i
            break

    acceptance = None
    fenced = False
    for i in range(start + 1, end):
        if FENCE_RE.match(lines[i]):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEAD_RE.match(lines[i])
        if m and m.group(2).strip().lower() == "acceptance":
            acceptance = i
            break
    if acceptance is None:
        return []

    out = []
    fenced = False
    for line in lines[acceptance + 1:end]:
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if HEAD_RE.match(line) or line.strip() == "---":
            break
        m = BULLET_RE.match(line)
        if m:
            out.append(m.group(1).strip())
    return out


def completeness(text, task_id, plan_path):
    """Rule 4. `plan_path` is already resolved, so ambiguity has been settled above."""
    required = task_criteria(read_text(plan_path), task_id)
    if required is None:
        return ["task %s has no single section in %s"
                % (task_id, os.path.basename(plan_path))]
    if not required:
        return ["task %s has no criteria under ### Acceptance in %s"
                % (task_id, os.path.basename(plan_path))]
    rows = criteria_rows(text)
    seen = set(r[0] for r in rows)
    missing = [c for c in required if c not in seen]
    reasons = []
    if missing:
        reasons.append("%d of %d criteria enumerated (missing: %s)"
                       % (len(required) - len(missing), len(required),
                          ", ".join(missing)))
    for rid, command, output, tok in rows:
        if not command:
            reasons.append("criteria row %s has no check command" % rid)
        elif not output:
            reasons.append("criteria row %s records no output" % rid)
        if tok is None:
            reasons.append("criteria row %s carries no verdict token" % rid)
        elif tok == "FAIL":
            reasons.append("criteria row %s is [FAIL]" % rid)
    return reasons


def validate(text, plan_root):
    """Every reason this return is invalid, in rule order. `plan_root` is the plan file or
    the directory to resolve one in; it is touched only when rule 4 needs it, so a stage
    return in a two-workstream pod is not refused for an ambiguity it never consults."""
    size = len(text.encode("utf-8"))
    if size > SIZE_CAP:
        return ["%d bytes, over the %d-byte cap" % (size, SIZE_CAP)]

    reasons = []
    keys = output_keys(text)
    verdict = None
    m = re.search(r"(?m)^VERDICT:[ \t]*(\S+)", text)
    if m is None:
        reasons.append("no VERDICT line")
    else:
        verdict = m.group(1).strip().lower()
        if verdict not in VERDICTS:
            reasons.append("VERDICT: %s is not one of %s"
                           % (m.group(1), ", ".join(VERDICTS)))
            verdict = None
    if "FINDINGS" not in keys:
        reasons.append("no FINDINGS: section")
    kind, required = declared_kind(keys)
    if kind is not None:
        absent = [k for k in required if k not in keys]
        if absent:
            reasons.append("%s kind is missing %s"
                           % (kind, ", ".join(k + ":" for k in absent)))
    if verdict == "done" and BLOCKING_RE.search(text):
        reasons.append("VERDICT: done with an open [blocking] finding")

    task = re.search(r"(?m)^TASK:[ \t]*(\S+)", text)
    if task is not None and verdict == "done":
        plan = plan_root if os.path.isfile(plan_root) else resolve_plan(plan_root)
        reasons.extend(completeness(text, task.group(1).strip(), plan))
    return reasons


def verdict_line(reasons):
    if not reasons:
        return "RETURN-GATE: OK", 0
    return "RETURN-GATE: REJECTED — " + "; ".join(reasons), 2


def is_handback(block):
    """A subagent's hand-back tool call, by which its report reaches its parent."""
    return (block.get("type") == "tool_use"
            and str(block.get("name") or "").lower().endswith("handback"))


def handback(block):
    payload = block.get("input")
    if not isinstance(payload, dict):
        return ""
    value = payload.get("message") or payload.get("text") or ""
    return value if isinstance(value, str) else ""


def last_assistant_text(transcript_path):
    """The subagent's last return, whichever way it was emitted: an assistant text block,
    or the `message` of a `SubagentHandback` tool call. `None` when the transcript is
    unreadable or carries neither — which is fail-closed, and deliberately: a hook that
    cannot read the return has not approved it."""
    try:
        lines = read_text(transcript_path).splitlines()
    except (OSError, UnicodeError):
        return None
    found = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue
        message = entry.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            blocks = [content]
        elif isinstance(content, list):
            blocks = [handback(b) if is_handback(b) else b.get("text", "")
                      for b in content
                      if isinstance(b, dict)
                      and (b.get("type") == "text" or is_handback(b))]
        else:
            blocks = []
        text = "\n".join(b for b in blocks if b)
        if text.strip():
            found = text
    return found


def log_reject(home, session_id, line):
    """Requirement 6 — every rejection is appended, and a log that cannot be written is
    never a reason to let the return through."""
    try:
        d = os.path.join(home, ".claude", "plan-guard", "rejects")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "%s.log" % (session_id or "unknown")), "a",
                  encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), line))
    except OSError:
        pass


def hook_mode():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    transcript = payload.get("transcript_path") or ""
    text = last_assistant_text(transcript) if transcript else None
    if text is None:
        line = ("RETURN-GATE: REJECTED — no return text found in %s"
                % (transcript or "<no transcript_path>"))
        code = 2
    else:
        cwd = payload.get("cwd") or os.getcwd()
        root = repo_root(cwd) or cwd
        try:
            line, code = verdict_line(validate(text, root))
        except Ambiguous as exc:
            line, code = "RETURN-GATE: ambiguous plan (%d matches)" % exc.n, 2
    sys.stderr.write(line + "\n")
    if code != 0:
        log_reject(os.path.expanduser("~"), payload.get("session_id"), line)
    return code


def file_mode(return_path, plan_path):
    try:
        text = read_text(return_path)
    except (OSError, UnicodeError) as exc:
        sys.stderr.write("return-gate: cannot read %s: %s\n" % (return_path, exc))
        return 2
    try:
        line, code = verdict_line(validate(text, plan_path))
    except Ambiguous as exc:
        line, code = "RETURN-GATE: ambiguous plan (%d matches)" % exc.n, 2
    sys.stdout.write(line + "\n")
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate a stage or task return against the live plan.")
    parser.add_argument("--hook", action="store_true",
                        help="hook mode: payload on stdin, the line on stderr")
    parser.add_argument("--return", dest="return_path",
                        help="file mode: the return's text")
    parser.add_argument("--plan", dest="plan_path",
                        help="file mode: the plan, or a directory to resolve one in")
    args = parser.parse_args(argv)
    if args.hook:
        if args.return_path or args.plan_path:
            parser.error("--hook takes its input from stdin; drop --return/--plan")
        return hook_mode()
    if not args.return_path or not args.plan_path:
        parser.error("file mode needs both --return and --plan")
    return file_mode(args.return_path, args.plan_path)


if __name__ == "__main__":
    sys.exit(main())

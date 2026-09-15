#!/usr/bin/env python3
"""M11 — the window is predicted, not discovered (`SPEC.md` § 13.1-13.2, R163).

  predict-spend.py --plan <path> [--window <dollars>]

Prints a per-task table, a total, the window and the source it was read from, and either
`within window` or a `DROP-LIST`. The output **is** the `## Predicted spend` section the
freeze gate requires, in `SPEC.md` § 17.7's shape. Exit `0` ok, `2` an unresolvable
`comparable`.

**The join is the plan's own `## Comparable ids` table, never a literal string search**
(Global constraint 13). A `comparable` id is `<corpus>-<row key>`; the id names a row in
that table, and the table's `corpus` cell names where on disk the row actually lives —
`r2` is `plans/archive/plan-v2-release-2/notes/SPEND.md`'s per-stage table, `r3` is this
run's own `STATE.md` ledger `**Spend:**` rows (for stages the predecessor session ran) and
the live `stage-spend.py <session>` stage table (for stages this session ran, the session
token itself read off the `## Comparable ids` table rather than hard-coded here). An id
absent from that table, or whose row key names no row in its corpus, is a hard error,
exit 2, naming the task and the id — never a silent zero. `none` prices at the corpus
**median** billed tokens per dispatch and counts as unmatched in the `Matched <n> of <n>`
line; the median is printed with every row it was computed from, so a reader audits the
number instead of trusting it.

`<window>` resolves to the `~$<n>` figure under `BRIEF.md`'s `## The bar` heading, with the
output naming the file **and line** it read. `--window <dollars>` is for fixtures only and
makes the output say `window: argument` instead of a file path, so a fixture run can never
be mistaken for a real one.

Stdlib only, Python 3.9.
"""
import argparse
import math
import os
import re
import subprocess
import sys

RATE_PER_MILLION = 0.635          # $ per million billed tokens (release 2: $173.94 / 273,955,454)
MIN_PER_DISPATCH = 31             # ~13h / 25 boundaries, release 2

TASK_ROW = re.compile(r"^\|\s*(T\d+)\s*\|")
BATCH_CELL = re.compile(r"^(b\d+|solo)$")
COMPARABLE_HEADING = re.compile(r"^##\s+Comparable ids\s*$")
ANY_HEADING = re.compile(r"^##\s+\S")
BAR_HEADING = re.compile(r"^##\s+The bar\b")
WINDOW_FIGURE = re.compile(r"~\$(\d+)")
BACKTICK = re.compile(r"`([^`]+)`")
HASH_HEADING_BACKTICK = re.compile(r"`(#{2,3}[^`]*)`")
THE_BLOCK = re.compile(r"[Tt]he (.+?) block")
SUBROW = re.compile(r"\s+\d[\d,]*(?:\s+calls)?\s*·\s*(?:peak\s+)?[\d,]+\s*·\s*(?:billed\s+)?([\d,]+)")


class ResolutionError(Exception):
    """A comparable id could not be resolved against its named corpus on disk."""


# --------------------------------------------------------------------- the plan, read

def plan_tasks(plan_path):
    """`(task, comparable)` for every row of the plan's task table. The predicted-spend
    table's own rows also begin `| T1 |`; the batch cell (a `b<n>`/`solo` token, absent
    from that other table) is what tells the two apart."""
    tasks = []
    with open(plan_path, encoding="utf-8") as fh:
        for line in fh:
            if not TASK_ROW.match(line):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 5 or not BATCH_CELL.match(cells[2]):
                continue
            tasks.append((cells[0], cells[4]))
    return tasks


def comparable_ids_table(plan_path):
    """`id -> (corpus text, row text)` from the plan's own `## Comparable ids` table —
    Global constraint 13's join, read as a table rather than grepped."""
    rows, inside = {}, False
    with open(plan_path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if COMPARABLE_HEADING.match(stripped):
                inside = True
                continue
            if inside and ANY_HEADING.match(line):
                break
            if not inside or not stripped.startswith("|"):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) != 4 or cells[0].lower() == "id" or set(cells[0]) <= set("-: "):
                continue
            rows[cells[0]] = (cells[1], cells[2])
    return rows


def resolve_window(args, plan_dir):
    if args.window is not None:
        return args.window, "argument"
    brief_path = os.path.join(plan_dir, "BRIEF.md")
    inside = False
    with open(brief_path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if BAR_HEADING.match(line.strip()):
                inside = True
                continue
            if inside and ANY_HEADING.match(line) and not BAR_HEADING.match(line.strip()):
                break
            if not inside:
                continue
            found = WINDOW_FIGURE.search(line)
            if found:
                return int(found.group(1)), "%s:%d" % (brief_path, lineno)
    raise ResolutionError("no `~$<n>` figure under %s's `## The bar`" % brief_path)


# ------------------------------------------------------------- the two corpora, on disk

def parse_stage_table(text, exclude=("stage", "orchestrator", "TOTAL")):
    """Whitespace-columned rows (`label  model  ...  billed`), the shape both
    `stage-spend.py`'s own printer and the archived `SPEND.md` fenced block use — the
    label is everything before the first run of 2+ spaces, billed is the last column."""
    rows = {}
    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip() or line.startswith("control:"):
            continue
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 2:
            continue
        label = parts[0]
        if label in exclude or label.startswith("codex"):
            continue
        try:
            billed = int(parts[-1].replace(",", ""))
        except ValueError:
            continue
        rows[label] = billed
    return rows


def r2_stage_table(pod_root):
    """release 2's `SPEND.md`, the `## Per-stage spend` fenced block — the 17-row table,
    not the later-appended `B7, B8, B9` markdown table, which is a different section."""
    path = os.path.join(pod_root, "plans", "archive", "plan-v2-release-2", "notes", "SPEND.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    idx = text.find("## Per-stage spend")
    if idx == -1:
        raise ResolutionError("no `## Per-stage spend` heading in %s" % path)
    fence_start = text.find("```", idx)
    fence_end = text.find("```", fence_start + 3)
    if fence_start == -1 or fence_end == -1:
        raise ResolutionError("no fenced stage table after `## Per-stage spend` in %s" % path)
    return path, parse_stage_table(text[fence_start + 3:fence_end])


def state_spend_block(state_path, heading_substr):
    """The `- **Spend:**` bullet (possibly wrapped across lines) under the first STATE.md
    heading containing `heading_substr`, joined to one line."""
    with open(state_path, encoding="utf-8") as fh:
        lines = fh.readlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^#{2,3}\s", line) and heading_substr.lower() in line.lower():
            start = i + 1
            break
    if start is None:
        raise ResolutionError("no STATE.md heading containing %r" % heading_substr)
    block, in_spend = [], False
    for line in lines[start:]:
        if re.match(r"^#{2,3}\s", line):
            break
        if re.match(r"^-\s+\*\*Spend:\*\*", line):
            in_spend = True
            block.append(line.strip())
            continue
        if in_spend:
            if re.match(r"^-\s+\*\*", line) or not line.strip():
                break
            block.append(line.strip())
    if not block:
        raise ResolutionError("no `**Spend:**` line under the STATE.md heading containing %r"
                              % heading_substr)
    return " ".join(block)


def state_heading_key(corpus_text):
    """The STATE.md heading `## Comparable ids` points a `comparable` id at, extracted
    from the table's own corpus prose rather than assumed — `` `### Stage B1 — Ground` ``
    names its heading directly; `` the Wave 0 block `` names it by paraphrase."""
    found = HASH_HEADING_BACKTICK.search(corpus_text)
    if found:
        return found.group(1).lstrip("#").strip()
    found = THE_BLOCK.search(corpus_text)
    if found:
        return found.group(1).strip()
    raise ResolutionError("no STATE.md heading named in corpus text %r" % corpus_text)


def live_stage_session(corpus_text):
    found = re.search(r"stage-spend\.py\s+(\S+)", corpus_text.replace("`", ""))
    if not found:
        raise ResolutionError("no session token in corpus text %r" % corpus_text)
    return found.group(1)


def live_stage_table(session, script_dir):
    stage_spend = os.path.join(script_dir, "stage-spend.py")
    proc = subprocess.run([sys.executable, stage_spend, session],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ResolutionError("stage-spend.py %s exited %d: %s"
                              % (session, proc.returncode, proc.stderr.strip()))
    label = "stage-spend.py %s" % session
    return label, parse_stage_table(proc.stdout)


# ------------------------------------------------------------------- resolving one id

def resolve_comparable(corpus_text, row_text, pod_root, plan_dir, script_dir):
    """`(billed, provenance)` for one `comparable` id's row, read from the corpus its own
    `## Comparable ids` cell names — never `None` silently; a miss raises or returns
    `None`, and the caller turns either into requirement 3's exit 2."""
    token = BACKTICK.search(row_text)
    row_key = token.group(1) if token else None
    if "SPEND.md" in corpus_text:
        source, table = r2_stage_table(pod_root)
        if row_key is None:
            return None
        billed = table.get(row_key)
        return None if billed is None else (billed, "%s (row %r)" % (source, row_key))
    if "stage-spend.py" in corpus_text:
        session = live_stage_session(corpus_text)
        source, table = live_stage_table(session, script_dir)
        if row_key is None:
            return None
        billed = table.get(row_key)
        return None if billed is None else (billed, "%s (row %r)" % (source, row_key))
    if "STATE.md" in corpus_text:
        state_path = os.path.join(plan_dir, "STATE.md")
        heading = state_heading_key(corpus_text)
        block = state_spend_block(state_path, heading)
        if row_key is not None:
            found = re.search(re.escape(row_key) + SUBROW.pattern, block)
            if not found:
                return None
            return (int(found.group(1).replace(",", "")),
                    "%s (heading %r, row %r)" % (state_path, heading, row_key))
        found = re.search(r"billed\s+([\d,]+)", block)
        if not found:
            return None
        return (int(found.group(1).replace(",", "")),
                "%s (heading %r)" % (state_path, heading))
    raise ResolutionError("corpus text %r names no known corpus" % corpus_text)


# --------------------------------------------------------------- the median, auditable

def median_corpus(comparable_ids, pod_root, plan_dir, script_dir):
    """Every per-dispatch row of both corpora, `orchestrator`/`TOTAL`/Codex rows excluded
    because none is a Claude-side dispatch billed in tokens. Printed with its rows so a
    reader can reproduce the number by opening the corpus (requirement 3, TA2)."""
    rows = {}
    try:
        _, table = r2_stage_table(pod_root)
        rows.update({"r2 %s" % k: v for k, v in table.items()})
    except ResolutionError:
        pass
    state_path = os.path.join(plan_dir, "STATE.md")
    for heading in ("Wave 0", "Stage B1"):
        try:
            block = state_spend_block(state_path, heading)
        except ResolutionError:
            continue
        for found in re.finditer(r"(W0[a-z])" + SUBROW.pattern, block):
            rows["r3 %s" % found.group(1)] = int(found.group(2).replace(",", ""))
        found = re.search(r"billed\s+([\d,]+)", block)
        if found and heading == "Stage B1":
            rows["r3 Stage B1 — Ground"] = int(found.group(1).replace(",", ""))
    session = None
    for corpus_text, _ in comparable_ids.values():
        if "stage-spend.py" in corpus_text:
            session = live_stage_session(corpus_text)
            break
    if session:
        try:
            _, table = live_stage_table(session, script_dir)
            rows.update({"r3 %s" % k: v for k, v in table.items()})
        except ResolutionError:
            pass
    ordered = sorted(rows.items(), key=lambda kv: kv[1])
    n = len(ordered)
    if n == 0:
        raise ResolutionError("no rows found in either corpus — cannot price `none`")
    if n % 2 == 1:
        median = ordered[n // 2][1]
    else:
        median = (ordered[n // 2 - 1][1] + ordered[n // 2][1]) / 2.0
    return median, ordered


# ------------------------------------------------------------------------- formatting

def fmt_int(n):
    return "{:,}".format(int(round(n)))


def fmt_money(n):
    """Floored to the cent (TA3) — the total is authoritative and derived from the
    summed tokens, never from summing already-floored per-row dollars."""
    return math.floor(n * 100) / 100.0


def dollars(billed):
    return fmt_money(billed * RATE_PER_MILLION / 1e6)


# ----------------------------------------------------------------------------- main

def build_table(plan_path, pod_root, plan_dir, script_dir):
    tasks = plan_tasks(plan_path)
    comparable_ids = comparable_ids_table(plan_path)
    median, median_rows = median_corpus(comparable_ids, pod_root, plan_dir, script_dir)
    rows, matched = [], 0
    for task_id, comparable in tasks:
        if comparable == "none":
            rows.append((task_id, comparable, median))
            continue
        if comparable not in comparable_ids:
            raise ResolutionError("comparable id %r (task %s) not found in the plan's "
                                  "`## Comparable ids` table" % (comparable, task_id))
        corpus_text, row_text = comparable_ids[comparable]
        result = resolve_comparable(corpus_text, row_text, pod_root, plan_dir, script_dir)
        if result is None:
            raise ResolutionError("comparable id %r (task %s): row %r not found in its "
                                  "named corpus" % (comparable, task_id, row_text))
        billed, _provenance = result
        rows.append((task_id, comparable, billed))
        matched += 1
    return rows, matched, median, median_rows


def render(rows, matched, median, median_rows, window, window_source):
    total_billed = sum(billed for _, _, billed in rows)
    total_dollars = dollars(total_billed)
    total_minutes = MIN_PER_DISPATCH * len(rows)

    out = ["## Predicted spend", "",
          "| task | comparable | billed est. | $ est. | min est. |",
          "|---|---|---|---|---|"]
    for task_id, comparable, billed in rows:
        out.append("| %s | %s | %s | %.2f | %d |"
                   % (task_id, comparable, fmt_int(billed), dollars(billed), MIN_PER_DISPATCH))
    out.append("")
    out.append("Total: $%.2f, %d min, over %d dispatches. Rate: $%s per million billed tokens"
               % (total_dollars, total_minutes, len(rows), RATE_PER_MILLION))
    out.append("(release 2: $173.94 / 273,955,454), %d min per dispatch (13h / 25 boundaries)."
               % MIN_PER_DISPATCH)
    out.append("Matched %d of %d tasks to a measured row." % (matched, len(rows)))
    out.append("")
    out.append("window: %s — ~$%s" % (window_source, fmt_int(window)))
    med_label = fmt_int(median) if float(median).is_integer() else "%.1f" % median
    out.append("median: %s over %d rows (min %s, max %s)"
               % (med_label, len(median_rows), fmt_int(median_rows[0][1]),
                  fmt_int(median_rows[-1][1])))
    for label, value in median_rows:
        out.append("  %s — %s" % (label, fmt_int(value)))
    out.append("")
    if total_dollars > window:
        delta = total_dollars - window
        out.append("DROP-LIST — predicted $%.2f against a $%s window, over by $%.2f"
                   % (total_dollars, fmt_int(window), delta))
        # Cheapest dollar loss first — a structural ordering, not a judged priority; the
        # brief reserves the scope call for the operator (R178, § 13.2).
        candidates = sorted(rows, key=lambda r: dollars(r[2]))
        for i, (task_id, comparable, billed) in enumerate(candidates, start=1):
            out.append("%d. %s — drop this cycle, comparable %s — saves $%.2f, %d min"
                       % (i, task_id, comparable, dollars(billed), MIN_PER_DISPATCH))
    else:
        out.append("within window")
    return "\n".join(out) + "\n"


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True, help="the plan to price")
    parser.add_argument("--window", type=float, default=None,
                        help="fixtures only — overrides the BRIEF.md-read window")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    plan_path = os.path.abspath(args.plan)
    plan_dir = os.path.dirname(plan_path)
    pod_root = os.path.dirname(os.path.dirname(plan_dir))
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        rows, matched, median, median_rows = build_table(plan_path, pod_root, plan_dir,
                                                          script_dir)
        window, window_source = resolve_window(args, plan_dir)
    except ResolutionError as exc:
        sys.stderr.write("predict-spend: %s\n" % exc)
        return 2
    sys.stdout.write(render(rows, matched, median, median_rows, window, window_source))
    return 0


if __name__ == "__main__":
    sys.exit(main())

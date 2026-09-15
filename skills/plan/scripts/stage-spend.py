#!/usr/bin/env python3
"""Per-stage spend for one build-session run, from the harness's own transcripts.

  stage-spend.py <id>[,<id>…]                     one row per dispatched stage
  stage-spend.py <id>[,<id>…] --orchestrator      one row per stage boundary
  stage-spend.py <id>[,<id>…] --batches <plan>    C8's batching detector
  stage-spend.py <id>[,<id>…] --routes <plan>     C14's seat detector
  stage-spend.py --controls <STATE.md>            C11's control-pair walk

<session> is a session id, a unique prefix of one, or a comma-separated chain of them;
boundaries are numbered continuously across a chain. Stdlib only, Python 3.9.
Exit: 0 ok · 2 the positive control failed · 3 a boundary over 500,000 · 4 an unruled
middle-band boundary with no handoff following it.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens", "output_tokens")
DEFAULT_PROJECTS = os.path.expanduser("~/.claude/projects")

# R154: a segment that has not dispatched has no `subagents/` directory beside its
# transcript, and reporting nothing for it is what made this run's own boundary
# unmeasurable. `orchestrator_only` carries that fact rather than hiding it.
Segment = collections.namedtuple("Segment", "dir jsonl orchestrator_only")

ORCH_ONLY_CONTROL = ("control: 0 spawnDepth-1 meta files, 0 boundary records, "
                     "0 resolved exactly once — no subagents directory: "
                     "orchestrator-only segment\n")


def resolve_session(prefix, projects_dir):
    hits = sorted(d for d in glob.glob(os.path.join(projects_dir, "*", prefix + "*"))
                  if os.path.isdir(os.path.join(d, "subagents")))
    if len(hits) == 1:
        metas = glob.glob(os.path.join(hits[0], "subagents", "*.meta.json"))
        # an existing but empty subagents/ is the same state, and takes the same branch
        return Segment(hits[0], session_jsonl(hits[0]), not metas)
    if hits:                                        # the `!= 1` ambiguity error, unchanged
        raise SystemExit("error: %d session directories match %r under %s"
                         % (len(hits), prefix, projects_dir))
    bare = sorted(glob.glob(os.path.join(projects_dir, "*", prefix + "*.jsonl")))
    if len(bare) != 1:
        raise SystemExit("error: %d session directories match %r under %s"
                         % (len(bare), prefix, projects_dir))
    return Segment(bare[0][:-len(".jsonl")], bare[0], True)


def resolve_chain(spec, projects_dir):
    return [resolve_session(p.strip(), projects_dir) for p in spec.split(",") if p.strip()]


def session_jsonl(session_dir):
    return os.path.join(os.path.dirname(session_dir),
                        os.path.basename(session_dir) + ".jsonl")


def usage_total(use):
    return sum(use.get(f, 0) or 0 for f in USAGE_FIELDS)


def records(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def call_totals(jsonl):
    """Distinct requestIds in order, each mapped to its LAST record's four-field total.
    LAST wins: the file writes streaming partials under one requestId with growing
    output_tokens, so keeping the first under-counts output (measured: probe A, 46,019
    against a harness-reported 46,142 — SPEC.md § 6.3)."""
    order, last = [], {}
    for rec in records(jsonl):
        if rec.get("type") != "assistant":
            continue
        rid = rec.get("requestId")
        if rid not in last:
            order.append(rid)
        last[rid] = usage_total(rec.get("message", {}).get("usage", {}))   # LAST wins
    return order, last


def load_agents(segment):
    if segment.orchestrator_only:
        return {}
    agents = {}
    for meta_path in sorted(glob.glob(os.path.join(segment.dir, "subagents",
                                                   "*.meta.json"))):
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        agent_id = os.path.basename(meta_path)[len("agent-"):-len(".meta.json")]
        meta["id"] = agent_id
        meta["jsonl"] = meta_path[:-len(".meta.json")] + ".jsonl"
        agents[agent_id] = meta
    return agents


def owning_stage(agent_id, agents):
    """Walk parentAgentId up to the spawnDepth-1 ancestor. A deeper child is never a stage
    of its own; its calls and tokens belong to the stage that dispatched it."""
    seen = set()
    while agent_id in agents and agents[agent_id].get("spawnDepth", 1) > 1:
        if agent_id in seen:
            raise SystemExit("error: parentAgentId cycle at %s" % agent_id)
        seen.add(agent_id)
        agent_id = agents[agent_id].get("parentAgentId")
    return agent_id


def reported_peaks(segment):
    """The harness's own `subagent_tokens` per dispatch, read out of the tool_result in the
    dispatching transcript. This is the positive control for `peak`."""
    out = {}
    paths = [segment.jsonl]
    paths += sorted(glob.glob(os.path.join(segment.dir, "subagents", "*.jsonl")))
    for path in paths:
        for rec in records(path):
            if rec.get("type") != "user":
                continue
            for block in rec.get("message", {}).get("content", []) or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                text = block.get("content")
                if isinstance(text, list):
                    text = " ".join(b.get("text", "") for b in text if isinstance(b, dict))
                found = re.search(r"subagent_tokens:\s*(\d+)", text or "")
                if found:
                    out[block.get("tool_use_id")] = int(found.group(1))
    return out


def stage_rows(segment):
    agents = load_agents(segment)
    rolled = {}
    for agent_id, meta in agents.items():
        order, last = call_totals(meta["jsonl"])
        owner = owning_stage(agent_id, agents) or "unattributed"
        acc = rolled.setdefault(owner, [0, 0])
        acc[0] += len(order)
        acc[1] += sum(last.values())
    rows = []
    for agent_id, meta in sorted(agents.items(), key=lambda kv: kv[1]["description"]):
        if meta.get("spawnDepth", 1) != 1:
            continue
        order, last = call_totals(meta["jsonl"])
        calls, billed = rolled.get(agent_id, [0, 0])
        model = meta.get("model") or "—"
        rows.append({"description": meta["description"], "model": model,
                     "seat": "claude:%s" % model if model != "—" else "—",
                     "calls": calls, "peak": last[order[-1]] if order else 0,
                     "billed": billed, "tool_use_id": meta.get("toolUseId")})
    if "unattributed" in rolled:
        calls, billed = rolled["unattributed"]
        rows.append({"description": "unattributed (no parent in this session)",
                     "model": "—", "seat": "—", "calls": calls, "peak": 0,
                     "billed": billed, "tool_use_id": None})
    return rows


def orchestrator_row(segment, label="orchestrator"):
    order, last = call_totals(segment.jsonl)
    return {"description": label, "model": "—", "seat": "—", "calls": len(order),
            "peak": last[order[-1]] if order else 0, "billed": sum(last.values()),
            "tool_use_id": None}


# ---------------------------------------------------------------- the Codex side (C14)

def codex_runs(pod):
    """`<pod>/evidence/codex-*/meta.json`. `evidence/` is gitignored, so these
    directories are the only record of a Codex dispatch; a `task` of None is reported
    UNATTRIBUTED rather than guessed (T2, X5)."""
    out = []
    for meta_path in sorted(glob.glob(os.path.join(pod, "evidence", "codex-*",
                                                   "meta.json"))):
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
        except (ValueError, OSError):
            continue
        meta["dir"] = os.path.basename(os.path.dirname(meta_path))
        out.append(meta)
    return out


def codex_seat(meta):
    seat = "codex:%s" % (meta.get("model") or "—")
    if meta.get("effort"):
        seat += ":%s" % meta["effort"]
    return seat


def codex_rows(pod):
    grouped = collections.OrderedDict()
    for meta in codex_runs(pod):
        key = (meta.get("task") or "unattributed", codex_seat(meta))
        grouped[key] = grouped.get(key, 0) + 1
    return [{"description": "codex %s" % task, "model": "—", "seat": seat,
             "calls": count, "peak": 0, "billed": 0, "tool_use_id": None}
            for (task, seat), count in grouped.items()]


# ------------------------------------------------------------------- the stage report

def print_stages(segments, pod, out=sys.stdout):
    rows, reported = [], {}
    multi = len(segments) > 1
    for segment in segments:
        if not segment.orchestrator_only:
            rows += stage_rows(segment)
            reported.update(reported_peaks(segment))
    for segment in segments:
        label = "orchestrator"
        if multi:
            label += " (%s)" % os.path.basename(segment.dir)[:8]
        rows.append(orchestrator_row(segment, label))
    rows += codex_rows(pod)
    out.write("%-38s %-8s %-22s %6s %10s %12s\n"
              % ("stage", "model", "seat", "calls", "peak", "billed"))
    for row in rows:
        out.write("%-38s %-8s %-22s %6d %10d %12d\n"
                  % (row["description"][:38], row["model"], row["seat"][:22],
                     row["calls"], row["peak"], row["billed"]))
    out.write("%-38s %-8s %-22s %6s %10s %12d\n"
              % ("TOTAL", "", "", "", "", sum(r["billed"] for r in rows)))
    if all(s.orchestrator_only for s in segments):
        out.write(ORCH_ONLY_CONTROL)              # a STATED zero, not a silent one
        return 0
    checked, bad = 0, []
    for row in rows:
        figure = reported.get(row["tool_use_id"])
        if figure is None:
            continue
        checked += 1
        if figure != row["peak"]:
            bad.append((row["description"], row["peak"], figure))
    out.write("control: peak == the harness's own subagent_tokens — %d checked, %d mismatched\n"
              % (checked, len(bad)))
    for description, peak, figure in bad:
        out.write("  MISMATCH %s: parsed %d, harness %d\n" % (description, peak, figure))
    if checked == 0:
        out.write("control: NOT RUNNABLE — no completed dispatch carries a usage block; "
                  "these numbers are unverified\n")
        return 2
    return 2 if bad else 0


STAGE_ID = re.compile(r"^B\d+(\s|$)")            # R93: STARTS WITH a stage id
# A dispatch is attributed by its own DECLARATION line, never by a mention. MEASURED on
# this run's transcripts: a loose `\bT\d+\b` over a brief that merely names the plan's
# tasks attributed all eighteen to one stage dispatch, and every batch and every route
# then read as a divergence.
TASK_DECLARATION = re.compile(r"^TASK:\s*(T\d+)\b", re.M)
TASK_LEADING = re.compile(r"^(T\d+)\b")
# § 17.4's shipped form, and only it: a hyphen is not an em dash, and a ruling for
# another boundary is not this one's.
BAND_RULING = re.compile(r"^\s*BAND-RULING:\s*boundary\s+(\d+)\s+—\s+R\S+\s*$")


def band(context):
    if context > 500000:
        return "over-500k STOP"
    if context >= 250000:
        return "250k-500k BLOCKING-FINDING"
    return "under-250k"


def band_rulings(state_path):
    if not state_path:
        return None                              # no ledger passed: no band check
    ruled = set()
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as fh:
            for line in fh:
                found = BAND_RULING.match(line.rstrip("\n"))
                if found:
                    ruled.add(int(found.group(1)))
    return ruled


def dispatch_blocks(segment, include_subagents=False):
    """Every `Agent` tool_use in order, paired with the assistant message that carried it.
    A batch is several blocks in ONE message, which is the whole distinction C8's detector
    measures, so the message identity is part of the key.

    `include_subagents` is off for the boundary table — a boundary is the ORCHESTRATOR's
    context — and on for C8 and C14, because R181 puts this release's eighteen task
    dispatches in a deputy controller's transcript rather than the orchestrator's, and a
    detector reading only the orchestrator would count none of them."""
    paths = [segment.jsonl]
    if include_subagents:
        paths += sorted(glob.glob(os.path.join(segment.dir, "subagents", "*.jsonl")))
    for path in paths:
        for rec in records(path):
            if rec.get("type") != "assistant":
                continue
            message_id = "%s#%s" % (path, rec.get("uuid") or rec.get("requestId"))
            context = usage_total(rec.get("message", {}).get("usage", {}))
            for block in rec.get("message", {}).get("content", []) or []:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") == "Agent"):
                    yield message_id, context, block


def boundary_rows(segments):
    """(row, segment index, is the last boundary of its segment) across the chain."""
    per_segment = []
    for segment in segments:
        agents = load_agents(segment)
        want = {m["toolUseId"]: m for m in agents.values()
                if m.get("spawnDepth", 1) == 1}
        found, seen = [], {}
        for _, context, block in dispatch_blocks(segment):
            if block.get("id") not in want:
                continue
            seen[block["id"]] = seen.get(block["id"], 0) + 1
            found.append((want[block["id"]]["description"], context))
        per_segment.append((segment, want, found, seen))
    return per_segment


def print_boundaries(segments, state_path, out=sys.stdout):
    per_segment = boundary_rows(segments)
    out.write("%-3s %-38s %-11s %10s  %s\n"
              % ("#", "description", "stage?", "context", "band"))
    index, middles, over, control_failed = 0, [], False, False
    want_n = found_n = once_n = 0
    for position, (segment, want, found, seen) in enumerate(per_segment):
        final_segment = position == len(per_segment) - 1
        for offset, (description, context) in enumerate(found, 1):
            index += 1
            out.write("%-3d %-38s %-11s %10d  %s\n"
                      % (index, description[:38],
                         "yes" if STAGE_ID.match(description) else "not a stage",
                         context, band(context)))
            if context > 500000:
                over = True
            elif context >= 250000:
                # § 4.4: satisfied iff it is the last boundary of a non-final segment
                handed_off = (not final_segment) and offset == len(found)
                if not handed_off:
                    middles.append((index, description, context))
        want_n += len(want)
        found_n += len(found)
        once_n += sum(1 for n in seen.values() if n == 1)
        duplicates = [k for k, n in seen.items() if n != 1]
        if len(found) != len(want) or duplicates or (not want
                                                     and not segment.orchestrator_only):
            control_failed = True
    if all(s.orchestrator_only for s in segments):
        out.write(ORCH_ONLY_CONTROL)
        return 0
    out.write("control: %d spawnDepth-1 meta files, %d boundary records, "
              "%d resolved exactly once\n" % (want_n, found_n, once_n))
    if control_failed:
        out.write("control: FAILED — a zero means the wrong session file, a duplicate means the "
                  "parse is matching on something other than the tool-use id\n")
        return 2
    if over:
        return 3
    ruled = band_rulings(state_path)
    if ruled is None:
        return 0
    unruled = [m for m in middles if m[0] not in ruled]
    for number, description, context in unruled:
        out.write("band: boundary %d (%s) at %d is in the 250k-500k band with no handoff "
                  "following it and no `BAND-RULING: boundary %d — R<id>` in %s\n"
                  % (number, description, context, number, state_path))
    return 4 if unruled else 0


# ---------------------------------------------------------- the plan table (C8 and C14)

TASK_ROW = re.compile(r"^\|\s*(T\d+)\s*\|")
BATCH_CELL = re.compile(r"^(b\d+|solo)$")


def plan_tasks(plan_path):
    """`(task, batch, route)` for every row of the plan's task table. The predicted-spend
    table's rows also begin `| T1 |`, so the batch cell's format is what separates them —
    keying on the first cell alone would double-count every task."""
    tasks = []
    with open(plan_path, encoding="utf-8") as fh:
        for line in fh:
            if not TASK_ROW.match(line):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4 or not BATCH_CELL.match(cells[2]):
                continue
            tasks.append((cells[0], cells[2], cells[3]))
    return tasks


def claude_dispatches(segments):
    """`task id -> [(message id, seat)]`, from the Agent tool_use blocks joined to the
    dispatch meta files by tool-use id."""
    out = collections.defaultdict(list)
    for segment in segments:
        agents = load_agents(segment)
        by_tool_use = {m["toolUseId"]: m for m in agents.values() if m.get("toolUseId")}
        for message_id, _, block in dispatch_blocks(segment, include_subagents=True):
            payload = block.get("input") or {}
            tasks = set(TASK_DECLARATION.findall(payload.get("prompt") or ""))
            if not tasks:
                leading = TASK_LEADING.match((payload.get("description") or "").strip())
                tasks = {leading.group(1)} if leading else set()
            meta = by_tool_use.get(block.get("id")) or {}
            seat = "claude:%s" % meta["model"] if meta.get("model") else "claude:—"
            for task in sorted(tasks):
                out[task].append((message_id, seat))
    return out


def print_batches(segments, plan_path, pod, out=sys.stdout):
    tasks = plan_tasks(plan_path)
    dispatched = claude_dispatches(segments)
    codex_by_task = collections.defaultdict(list)
    for meta in codex_runs(pod):
        if meta.get("task"):
            codex_by_task[meta["task"]].append(meta["dir"])
    groups = collections.OrderedDict()
    for task, batch, _ in tasks:
        if batch == "solo":
            continue                              # a solo task is not a batch
        groups.setdefault(batch, []).append(task)
    if not groups:
        out.write("batches: the plan's task table names no `b<n>` group\n")
        return 0
    for batch, members in groups.items():
        messages = set()
        for task in members:
            messages.update(mid for mid, _ in dispatched.get(task, []))
        count = len(messages) + sum(len(codex_by_task.get(t, [])) for t in members)
        if count == 0:
            verdict = "no dispatch recorded"
        elif count == 1:
            verdict = "ok"
        else:
            verdict = "DIVERGENCE (expected 1)"
        out.write("batch %s: %d task%s, %d dispatch%s — %s\n"
                  % (batch, len(members), "" if len(members) == 1 else "s",
                     count, "" if count == 1 else "es", verdict))
    return 0                                      # a Finding, never a halt


def print_routes(segments, plan_path, pod, out=sys.stdout):
    tasks = plan_tasks(plan_path)
    dispatched = claude_dispatches(segments)
    runs = codex_runs(pod)
    codex_by_task = collections.defaultdict(list)
    for meta in runs:
        if meta.get("task"):
            codex_by_task[meta["task"]].append(codex_seat(meta))
    for task, _, declared in tasks:
        seats = [seat for _, seat in dispatched.get(task, [])] + codex_by_task.get(task, [])
        seen = sorted(set(seats))
        if not seen:
            out.write("%s: declared %s · recorded none — no dispatch recorded\n"
                      % (task, declared))
            continue
        recorded = "+".join(seen)
        out.write("%s: declared %s · recorded %s — %s\n"
                  % (task, declared, recorded,
                     "ok" if seen == [declared] else "DIVERGENCE"))
    for meta in runs:
        if not meta.get("task"):
            out.write("UNATTRIBUTED codex dispatch: evidence/%s carries `task: null` — "
                      "the seat is recorded and the task is not guessed\n" % meta["dir"])
    return 0                                      # a Finding, never a halt


# --------------------------------------------------- `--controls`, C11's acceptance (T2)

CRITERION_ID = re.compile(r"\bA(?:C)?\d+(?:-[A-Za-z0-9]+)*\b")
# R184's criteria row, which is the form a task return carries into the ledger.
LEDGER_ROW = re.compile(r"^\s*[-*]\s*\[([A-Za-z][A-Za-z0-9-]*)\]\s*(.*)$")


def key_table_rows(spec_path):
    """§ 18's key table, read AS A TABLE — `C1` is a prefix of `C11`, so grepping a key
    is the defect this walk exists to avoid."""
    if not os.path.exists(spec_path):
        return []
    rows, inside = [], False
    with open(spec_path, encoding="utf-8") as fh:
        for line in fh:
            if re.match(r"^##\s+18\.", line):
                inside = True
                continue
            if inside and re.match(r"^##\s+\d+\.", line):
                break
            if not inside or not line.lstrip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 3 or cells[0].lower() == "key" or set(cells[0]) <= set("-: "):
                continue
            rows.append(cells)
    return rows


def ledger_outputs(state_path):
    """`criterion id -> what it printed`, from the criteria rows a task return leaves in
    the ledger. A row with nothing after the arrow is *unrecorded*, not resolved."""
    out = {}
    with open(state_path, encoding="utf-8") as fh:
        for line in fh:
            found = LEDGER_ROW.match(line.rstrip("\n"))
            if not found:
                continue
            rest = found.group(2)
            printed = rest.split("→", 1)[1].strip() if "→" in rest else ""
            printed = re.sub(r"\s*\[(PASS|FAIL)\]\s*$", "", printed).strip()
            if printed:
                out[found.group(1)] = printed
    return out


def quote(text, width=44):
    return text if len(text) <= width else text[:width].rstrip() + " …"


def print_controls(state_path, out=sys.stdout):
    spec_path = os.path.join(os.path.dirname(os.path.abspath(state_path)), "SPEC.md")
    rows = key_table_rows(spec_path)
    if not rows:
        out.write("controls: the key table did not parse — no § 18 table in %s\n"
                  % spec_path)
        return 2                                  # blocked, and never a pass
    printed = ledger_outputs(state_path)
    unresolved = []
    for key, violating, passing in rows:
        parts, ok = [], True
        for label, cell in (("violating", violating), ("passing", passing)):
            ids = CRITERION_ID.findall(cell)
            if not ids:
                ok = False
                parts.append("%s — ✗ (no criterion named)" % label)
                continue
            marks = []
            for criterion in ids:
                if criterion in printed:
                    marks.append('%s ✓ "%s"' % (criterion, quote(printed[criterion])))
                else:
                    marks.append("%s ✗ (not recorded)" % criterion)
                    ok = False
            parts.append("%s %s" % (label, " / ".join(marks)))
        out.write("%s: %s\n" % (key, " · ".join(parts)))
        if not ok:
            unresolved.append(key)
    if unresolved:
        out.write("unresolved: %s\n" % ", ".join(unresolved))
        return 1
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("session", nargs="?",
                        help="a session id, a prefix, or a comma-separated chain")
    parser.add_argument("--projects-dir", default=DEFAULT_PROJECTS)
    parser.add_argument("--pod", default=os.getcwd(),
                        help="the pod whose evidence/codex-*/meta.json names the Codex seats")
    parser.add_argument("--orchestrator", action="store_true",
                        help="print one row per stage boundary instead of per stage")
    parser.add_argument("--state", help="the ledger the band check reads (SPEC.md § 4.4)")
    parser.add_argument("--batches", metavar="PLAN", help="C8's batching detector")
    parser.add_argument("--routes", metavar="PLAN", help="C14's route detector")
    parser.add_argument("--controls", metavar="STATE",
                        help="C11's control-pair walk over SPEC.md § 18")
    args = parser.parse_args(argv)
    if args.controls:
        if args.session:
            parser.error("--controls is a mode and takes no session positional")
        for name in ("orchestrator", "batches", "routes"):
            if getattr(args, name):
                parser.error("--controls is a mode and does not combine with --%s" % name)
    elif not args.session:
        parser.error("a session id, a prefix, or a comma-separated chain is required")
    return args


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.controls:
        return print_controls(args.controls)
    segments = resolve_chain(args.session, args.projects_dir)
    if args.batches:
        return print_batches(segments, args.batches, args.pod)
    if args.routes:
        return print_routes(segments, args.routes, args.pod)
    if args.orchestrator:
        return print_boundaries(segments, args.state)
    return print_stages(segments, args.pod)


if __name__ == "__main__":
    sys.exit(main())

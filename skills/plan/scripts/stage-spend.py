#!/usr/bin/env python3
"""Per-stage spend for one build-session run, from the harness's own transcripts.

  stage-spend.py <session>                 one row per dispatched stage
  stage-spend.py <session> --orchestrator  one row per stage boundary

<session> is a session id or a unique prefix of one. Stdlib only, Python 3.9.
Exit: 0 ok · 2 the positive control failed · 3 a boundary over 500,000.
"""
import argparse
import glob
import json
import os
import re
import sys

USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens", "output_tokens")
DEFAULT_PROJECTS = os.path.expanduser("~/.claude/projects")


def resolve_session(prefix, projects_dir):
    hits = sorted(d for d in glob.glob(os.path.join(projects_dir, "*", prefix + "*"))
                  if os.path.isdir(os.path.join(d, "subagents")))
    if len(hits) != 1:
        raise SystemExit("error: %d session directories match %r under %s"
                         % (len(hits), prefix, projects_dir))
    return hits[0]


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


def load_agents(session_dir):
    agents = {}
    for meta_path in sorted(glob.glob(os.path.join(session_dir, "subagents", "*.meta.json"))):
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


def reported_peaks(session_dir):
    """The harness's own `subagent_tokens` per dispatch, read out of the tool_result in the
    dispatching transcript. This is the positive control for `peak`."""
    out = {}
    paths = [session_jsonl(session_dir)]
    paths += sorted(glob.glob(os.path.join(session_dir, "subagents", "*.jsonl")))
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


def stage_rows(session_dir):
    agents = load_agents(session_dir)
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
        rows.append({"description": meta["description"], "model": meta.get("model") or "—",
                     "calls": calls, "peak": last[order[-1]] if order else 0,
                     "billed": billed, "tool_use_id": meta.get("toolUseId")})
    if "unattributed" in rolled:
        calls, billed = rolled["unattributed"]
        rows.append({"description": "unattributed (no parent in this session)", "model": "—",
                     "calls": calls, "peak": 0, "billed": billed, "tool_use_id": None})
    return rows


def orchestrator_row(session_dir):
    order, last = call_totals(session_jsonl(session_dir))
    return {"description": "orchestrator", "model": "—", "calls": len(order),
            "peak": last[order[-1]] if order else 0, "billed": sum(last.values()),
            "tool_use_id": None}


def print_stages(session_dir, out=sys.stdout):
    rows = stage_rows(session_dir) + [orchestrator_row(session_dir)]
    reported = reported_peaks(session_dir)
    out.write("%-38s %-8s %6s %10s %12s\n" % ("stage", "model", "calls", "peak", "billed"))
    for row in rows:
        out.write("%-38s %-8s %6d %10d %12d\n"
                  % (row["description"][:38], row["model"], row["calls"], row["peak"],
                     row["billed"]))
    out.write("%-38s %-8s %6s %10s %12d\n"
              % ("TOTAL", "", "", "", sum(r["billed"] for r in rows)))
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


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("session", help="a session id or a unique prefix of one")
    parser.add_argument("--projects-dir", default=DEFAULT_PROJECTS)
    parser.add_argument("--orchestrator", action="store_true",
                        help="print one row per stage boundary instead of per stage")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    session_dir = resolve_session(args.session, args.projects_dir)
    if args.orchestrator:
        return print_boundaries(session_dir)          # Task 11
    return print_stages(session_dir)


if __name__ == "__main__":
    sys.exit(main())

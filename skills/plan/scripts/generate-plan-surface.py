#!/usr/bin/env python3
"""Generate the plan surface tree from an append-only log.jsonl.

Usage:  generate-plan-surface.py <plan-dir>
        generate-plan-surface.py --stdout <plan-dir>

Reads <plan-dir>/log.jsonl and writes (or prints) the five generated files:
  INDEX.md  decisions.md  assumptions.md  questions.md  .plan.yaml

The log is the source of truth; the tree is a projection.  Nothing in the
tree is hand-edited — a change is an append to the log, never an edit.

Event vocabulary (SPEC §3, 17 events):
  vision-set  branch-sketched  branch-detailed  wave-opened  wave-closed
  goal-emitted  goal-skipped  decision-made  assumption-recorded
  assumption-falsified  question-opened  question-resolved  gate-passed
  verdict-recorded  run-record-written  lane-chosen  funnel-run
"""

import json
import os
import sys
from collections import OrderedDict
from datetime import datetime

EVENTS = {
    "vision-set", "branch-sketched", "branch-detailed", "wave-opened",
    "wave-closed", "goal-emitted", "goal-skipped", "decision-made",
    "assumption-recorded", "assumption-falsified", "question-opened",
    "question-resolved", "gate-passed", "verdict-recorded",
    "run-record-written", "lane-chosen", "funnel-run",
}


def die(msg):
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_log(path):
    entries = []
    with open(path, "r") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                die(f"log.jsonl line {i}: bad JSON: {e}")
            ev = entry.get("event")
            if ev not in EVENTS:
                die(f"log.jsonl line {i}: unknown event '{ev}'")
            entries.append(entry)
    return entries


def replay(entries):
    """Replay the log into structured state."""
    state = {
        "vision": None,
        "branches": OrderedDict(),   # slug -> {name, summary, status, goals}
        "waves": [],                  # [{id, branch, status, opened, closed}]
        "current_wave": None,
        "decisions": [],             # [{id, date, title, why, implications}]
        "assumptions": [],           # [{id, date, text, provenance, confidence, dependents, status}]
        "questions": [],             # [{id, date, text, resolution, status}]
        "gates": [],                 # [{goal_id, gate, date}]
        "verdicts": [],              # [{goal_id, date, result, detail}]
        "run_records": [],           # [{id, date, detail}]
    }

    for entry in entries:
        ev = entry["event"]
        ts = entry.get("timestamp", "")
        data = entry.get("data", {})

        if ev == "vision-set":
            state["vision"] = {
                "title": data.get("title", ""),
                "summary": data.get("summary", ""),
                "date": ts,
            }

        elif ev == "branch-sketched":
            slug = data.get("slug", "")
            state["branches"][slug] = {
                "name": data.get("name", slug),
                "summary": data.get("summary", ""),
                "status": "sketched",
                "goals": OrderedDict(),
            }

        elif ev == "branch-detailed":
            slug = data.get("slug", "")
            if slug in state["branches"]:
                state["branches"][slug]["status"] = "detailed"

        elif ev == "wave-opened":
            wave_id = data.get("wave_id", f"wave-{len(state['waves'])+1}")
            branch = data.get("branch", "")
            w = {"id": wave_id, "branch": branch, "status": "open",
                 "opened": ts, "closed": None}
            state["waves"].append(w)
            state["current_wave"] = wave_id

        elif ev == "wave-closed":
            wave_id = data.get("wave_id", "")
            for w in state["waves"]:
                if w["id"] == wave_id:
                    w["status"] = "closed"
                    w["closed"] = ts
            if state["current_wave"] == wave_id:
                state["current_wave"] = None

        elif ev == "goal-emitted":
            branch = data.get("branch", "")
            goal_id = data.get("goal_id", "")
            if branch in state["branches"]:
                state["branches"][branch]["goals"][goal_id] = {
                    "title": data.get("title", ""),
                    "status": "emitted",
                    "wave": data.get("wave", ""),
                }

        elif ev == "goal-skipped":
            branch = data.get("branch", "")
            goal_id = data.get("goal_id", "")
            reason = data.get("reason", "")
            if branch in state["branches"] and goal_id in state["branches"][branch]["goals"]:
                state["branches"][branch]["goals"][goal_id]["status"] = "skipped"
                state["branches"][branch]["goals"][goal_id]["skip_reason"] = reason

        elif ev == "decision-made":
            state["decisions"].append({
                "id": data.get("id", f"D{len(state['decisions'])+1}"),
                "date": ts,
                "title": data.get("title", ""),
                "why": data.get("why", ""),
                "implications": data.get("implications", ""),
            })

        elif ev == "assumption-recorded":
            state["assumptions"].append({
                "id": data.get("id", f"A{len(state['assumptions'])+1}"),
                "date": ts,
                "text": data.get("text", ""),
                "provenance": data.get("provenance", ""),
                "confidence": data.get("confidence", ""),
                "dependents": data.get("dependents", []),
                "status": "open",
            })

        elif ev == "assumption-falsified":
            aid = data.get("id", "")
            for a in state["assumptions"]:
                if a["id"] == aid:
                    a["status"] = "falsified"
                    a["falsified_date"] = ts
                    a["falsified_reason"] = data.get("reason", "")

        elif ev == "question-opened":
            state["questions"].append({
                "id": data.get("id", f"Q{len(state['questions'])+1}"),
                "date": ts,
                "text": data.get("text", ""),
                "resolves_when": data.get("resolves_when", ""),
                "status": "open",
            })

        elif ev == "question-resolved":
            qid = data.get("id", "")
            for q in state["questions"]:
                if q["id"] == qid:
                    q["status"] = "resolved"
                    q["resolved_date"] = ts
                    q["resolution"] = data.get("resolution", "")

        elif ev == "gate-passed":
            state["gates"].append({
                "goal_id": data.get("goal_id", ""),
                "gate": data.get("gate", ""),
                "date": ts,
            })
            # Update goal status
            goal_id = data.get("goal_id", "")
            for br in state["branches"].values():
                if goal_id in br["goals"]:
                    g = br["goals"][goal_id]
                    gate = data.get("gate", "")
                    if gate == "gate-1":
                        g["status"] = "gate-1-passed"
                    elif gate == "gate-2":
                        g["status"] = "gate-2-passed"

        elif ev == "verdict-recorded":
            state["verdicts"].append({
                "goal_id": data.get("goal_id", ""),
                "date": ts,
                "result": data.get("result", ""),
                "detail": data.get("detail", ""),
            })

        elif ev == "run-record-written":
            state["run_records"].append({
                "id": data.get("id", f"RR{len(state['run_records'])+1}"),
                "date": ts,
                "goal_id": data.get("goal_id", ""),
                "detail": data.get("detail", ""),
            })

    return state


def render_index(state):
    lines = []
    v = state["vision"]
    if v:
        lines.append(f"# {v['title']}")
        lines.append("")
        lines.append(f"> {v['summary']}")
        lines.append("")
    else:
        lines.append("# Plan")
        lines.append("")

    # Current wave
    if state["current_wave"]:
        lines.append(f"**Current wave:** {state['current_wave']}")
        lines.append("")

    # Branch map
    lines.append("## Branch map")
    lines.append("")
    lines.append("| Branch | Status | Goals |")
    lines.append("|---|---|---|")
    for slug, br in state["branches"].items():
        goal_count = len(br["goals"])
        goal_summary = f"{goal_count} goal(s)" if goal_count else "—"
        lines.append(f"| {br['name']} | {br['status']} | {goal_summary} |")
    lines.append("")

    # Goals detail per branch
    for slug, br in state["branches"].items():
        if br["goals"]:
            lines.append(f"### {br['name']} — goals")
            lines.append("")
            lines.append("| Goal | Status |")
            lines.append("|---|---|")
            for gid, g in br["goals"].items():
                status = g["status"]
                if status == "skipped":
                    status = f"skipped — {g.get('skip_reason', '')}"
                lines.append(f"| {gid}: {g['title']} | {status} |")
            lines.append("")

    # Wave history
    if state["waves"]:
        lines.append("## Waves")
        lines.append("")
        lines.append("| Wave | Branch | Status | Opened | Closed |")
        lines.append("|---|---|---|---|---|")
        for w in state["waves"]:
            closed = w["closed"] or "—"
            lines.append(f"| {w['id']} | {w['branch']} | {w['status']} | {w['opened']} | {closed} |")
        lines.append("")

    # Gate / verdict summary
    if state["gates"] or state["verdicts"]:
        lines.append("## Verification")
        lines.append("")
        if state["gates"]:
            for g in state["gates"]:
                lines.append(f"- **{g['goal_id']}** passed {g['gate']} ({g['date']})")
        if state["verdicts"]:
            for v in state["verdicts"]:
                lines.append(f"- **{v['goal_id']}** verdict: {v['result']} ({v['date']})")
        lines.append("")

    # Run records
    if state["run_records"]:
        lines.append("## Run records")
        lines.append("")
        for rr in state["run_records"]:
            lines.append(f"- {rr['id']}: goal {rr['goal_id']} ({rr['date']})")
        lines.append("")

    return "\n".join(lines) + "\n"


def render_decisions(state):
    lines = ["# Decisions", ""]
    lines.append("| ID | Date | Decision | Why | Implications |")
    lines.append("|---|---|---|---|---|")
    for d in state["decisions"]:
        lines.append(f"| {d['id']} | {d['date']} | {d['title']} | {d['why']} | {d['implications']} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_assumptions(state):
    lines = ["# Assumptions", ""]
    lines.append("| ID | Date | Assumption | Provenance | Confidence | Dependents | Status |")
    lines.append("|---|---|---|---|---|---|---|")
    for a in state["assumptions"]:
        deps = ", ".join(a["dependents"]) if a["dependents"] else "—"
        status = a["status"]
        if status == "falsified":
            status = f"falsified ({a.get('falsified_date', '')}): {a.get('falsified_reason', '')}"
        lines.append(
            f"| {a['id']} | {a['date']} | {a['text']} | {a['provenance']} "
            f"| {a['confidence']} | {deps} | {status} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def render_questions(state):
    lines = ["# Questions", ""]
    lines.append("| ID | Date | Question | Resolves when | Status |")
    lines.append("|---|---|---|---|---|")
    for q in state["questions"]:
        status = q["status"]
        if status == "resolved":
            status = f"resolved ({q.get('resolved_date', '')}): {q.get('resolution', '')}"
        lines.append(
            f"| {q['id']} | {q['date']} | {q['text']} "
            f"| {q['resolves_when']} | {status} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def render_plan_yaml(state):
    """Render .plan.yaml — machine-readable state summary."""
    lines = ["# Auto-generated from log.jsonl — do not hand-edit"]
    v = state["vision"]
    if v:
        lines.append(f"vision: \"{v['title']}\"")
    else:
        lines.append("vision: null")

    lines.append(f"current_wave: {state['current_wave'] or 'null'}")

    lines.append("branches:")
    for slug, br in state["branches"].items():
        lines.append(f"  {slug}:")
        lines.append(f"    name: \"{br['name']}\"")
        lines.append(f"    status: {br['status']}")
        lines.append(f"    goals:")
        if br["goals"]:
            for gid, g in br["goals"].items():
                lines.append(f"      {gid}:")
                lines.append(f"        title: \"{g['title']}\"")
                lines.append(f"        status: {g['status']}")
        else:
            lines.append(f"      {{}}")

    lines.append("waves:")
    for w in state["waves"]:
        lines.append(f"  - id: {w['id']}")
        lines.append(f"    branch: {w['branch']}")
        lines.append(f"    status: {w['status']}")

    lines.append(f"decisions: {len(state['decisions'])}")
    open_assumptions = sum(1 for a in state["assumptions"] if a["status"] == "open")
    lines.append(f"assumptions_open: {open_assumptions}")
    open_questions = sum(1 for q in state["questions"] if q["status"] == "open")
    lines.append(f"questions_open: {open_questions}")
    lines.append(f"run_records: {len(state['run_records'])}")

    return "\n".join(lines) + "\n"


def main():
    mode = "write"
    args = sys.argv[1:]
    if args and args[0] == "--stdout":
        mode = "stdout"
        args = args[1:]

    if not args:
        die("usage: generate-plan-surface.py [--stdout] <plan-dir>")

    plan_dir = args[0].rstrip("/")
    log_path = os.path.join(plan_dir, "log.jsonl")
    if not os.path.isfile(log_path):
        die(f"no log.jsonl in {plan_dir}")

    entries = load_log(log_path)
    state = replay(entries)

    files = {
        "INDEX.md": render_index(state),
        "decisions.md": render_decisions(state),
        "assumptions.md": render_assumptions(state),
        "questions.md": render_questions(state),
        ".plan.yaml": render_plan_yaml(state),
    }

    if mode == "stdout":
        for name, content in files.items():
            print(f"=== {name} ===")
            print(content)
    else:
        for name, content in files.items():
            path = os.path.join(plan_dir, name)
            with open(path, "w") as f:
                f.write(content)
        print(f"Generated 5 files in {plan_dir}/")


if __name__ == "__main__":
    main()

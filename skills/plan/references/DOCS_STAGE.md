# The documentation stage

## The eight items

Eight items. Each is **changed** or **confirmed unchanged with a reason** — never silently skipped —
and the result is committed as `plans/<slug>/DOCS.md`:

| # | Item | What "changed" means |
|---|---|---|
| 1 | `ARCHITECTURE.md` | the system the pod builds moved; under 300 lines after the edit |
| 2 | `CONTEXT.md` | a term resolved, was renamed, or entered the avoid-list |
| 3 | `docs/adr/` index | a decision made during the run that is hard to reverse, surprising, and a real trade-off |
| 4 | `README.md` | only if **what the pod produces** changed — not if only its internals did |
| 5 | `RUN_REPORT.md` | one entry for the run, always added |
| 6 | `plans/INDEX.md` | the workstream's row updated |
| 7 | graphify | re-run where the pod holds code; a documents-only pod records "index tree satisfies the graph rule" |
| 8 | `scripts/docs-graph-check.py` | run; findings triaged into *this workstream's* and *the pod's baseline* |

`writing-documentation` is the prose rule for anything written here, and CCDK's is the editing rule:
document the **is-state**, never the change; start at the nearest document and escalate only on real
architectural impact.

## What item 8 fixes and what it records

The docs stage fixes what the brief explicitly names: `README.md` must link `ARCHITECTURE.md`,
`CONTEXT.md`, `docs/adr/`, `plans/INDEX.md` and `research/INDEX.md`. It also fixes every finding
naming a file this workstream created or edited. **Everything else the script reports is recorded,
not fixed** — bulk-adding another workstream's untracked research on this branch would bundle work
this branch did not do into this branch's diff. `DOCS.md` carries the pod's measured baseline and
the delta this run made to it, and the report carries a recommendation.

The baseline measured on 2026-09-12, before any fix: **175 findings — 67 `missing`, 58 `orphan`,
41 `untracked`, 9 `oversize`.** That count predates the `EXCLUDED` fix, the `serves:` check, and
both size exemptions (`SIZE_EXEMPT` and `SIZE_EXEMPT_GLOB`) below — none of them existed when it was
taken, so a current run measures a different number, `no-serves` and `exempt` counts included.

The merged estate graph that would let a model cross pods is a control-plane open loop. The docs
stage records the pointer — `~/cortexos-bakeoff-lab/MAP.md`, in-container
`/home/node/control-plane/MAP.md` — and does nothing else about it. It also adds the terms this
spec introduces to `CONTEXT.md`, which does not yet carry them: **Stage**, **Spine**, **Round**,
**Finding** (`blocking` / `advisory`), **Advisor packet**, **Verdict**, **Ledger**, **Land**,
**Output kind**. None conflicts with an existing entry.

## The DOCS.md template

```markdown
---
workstream: <slug>
serves: both
type: docs-checklist
surface: claude-code
updated: YYYY-MM-DD
---

# DOCS — <workstream title>

## The eight items

| # | Item | Changed / Confirmed | What, or why not |
|---|---|---|---|
| 1 | `ARCHITECTURE.md` | | |
| 2 | `CONTEXT.md` | | |
| 3 | `docs/adr/` index | | |
| 4 | `README.md` | | |
| 5 | `RUN_REPORT.md` | | |
| 6 | `plans/INDEX.md` | | |
| 7 | graphify | | |
| 8 | `docs-graph-check.py` | | |

Every row is **Changed** or **Confirmed unchanged** with a reason. Never blank, never skipped.

## The pod's documentation graph

**Baseline, measured <date> before any fix:** <total> findings — <n> `missing`, <n> `orphan`,
<n> `untracked`, <n> `oversize`, <n> `no-serves`, <n> `too-deep`.
**After this workstream's own fixes:** <total> findings — <same six counts>.
**Delta:** <what moved, and why>.
**Size-exempt files:** <path>, <n> lines, <which exemption> — one line per `exempt:` line the
run printed, `SIZE_EXEMPT` and `SIZE_EXEMPT_GLOB` alike.

**This workstream's own diff, the gate:** `docs-graph-check.py`'s findings intersected with
`git diff --name-only <base>...HEAD` = <the intersection, or "empty">.

**Recorded, not fixed** — pre-existing debt this branch did not introduce, with a recommendation:
<list>.

**Merged estate graph:** a control-plane open loop. Pointer only —
`~/cortexos-bakeoff-lab/MAP.md`, in-container `/home/node/control-plane/MAP.md`.

## The post-merge check

Run on the merged result, scoped the same way: findings ∩
`git diff --name-only <base>...<merge commit>` = <the intersection, or "empty">.
Exit code: <n>.
```

## What docs-graph-check.py checks

Python 3, standard library only, no external tool. `lychee` is not installed on this machine and
MkDocs strict mode needs a site config plus a nav file duplicating the index — both were considered
and rejected; the documentation scan already favoured the script.

**Flags.** `--root DIR` (default: the git top level), `--start FILE` (default `README.md`),
`--profile pod|package` (default `pod`).

**One exclusion predicate, applied to everything.** `EXCLUDED` is a constant at the top of the
file — `.git`, `.claude`, `.superpowers`, `node_modules`, `__pycache__`, `.venv*`, `outputs`,
`evidence`, `inputs`, `subprojects/*` — carrying one comment: a name belongs there only because the
pod's `.gitignore` deliberately keeps that directory out. The **same predicate** gates the
candidate set, the breadth-first walk, and all five checks below — applying it to candidates but not
to the reached set is how gitignored-by-design files got reported `untracked`, and one predicate is
what stops that recurring. A link *to* an excluded file still resolves for the broken-reference
check — the file exists, so it is not `missing` — but the target itself is never walked, sized,
tracked-checked or frontmatter-checked.

**Two size exemptions**, both by name in the source rather than waived by argument each run, and
both reported with their sizes in `DOCS.md` so neither can be silent. Each prints as its own
`exempt:` line — a report, not a finding, and it never sets the exit code.

`SIZE_EXEMPT` holds **`RUN_REPORT.md`**, matched by basename: a file that is **appended to by
contract** cannot live under a line cap, and the docs stage's own item 5 appends to this one every
run.

`SIZE_EXEMPT_GLOB` holds **`plans/*/*.md`** and **`plans/archive/*/*.md`**, matched by relative
path one glob segment at a time so `*` never crosses a separator — a workstream's own `BRIEF`,
`SPEC`, `PLAN`, `STATE` and `DOCS`. The spec measured this workstream's own `SPEC.md` at 849 lines
and its `PLAN.md` at 2,692 against a 500-line leaf budget, so acceptance criterion 5's intersection
could never be empty without this exemption. A workstream artifact is a **third document kind**, the
way `ARCHITECTURE.md` is a second one in ADR 0002: its length is a function of the work it records,
not of how readable it is as doctrine, and a correctly-written plan is long by construction. A cap a
correctly-written artifact cannot meet is the unreachable gate the spec already refused once at B8's
Land step — this is the same ruling applied twice.

Five checks in one pass; exit 0 clean, exit 1 with one finding per line as `<kind>: <path>:
<detail>`:

1. **Reachability** — breadth-first from `--start` over markdown links, resolved relative to the
   containing file, after stripping fenced blocks and inline code spans: a document that quotes
   link syntax otherwise yields phantom targets. Unreached is `orphan`.
2. **Broken reference** — a link target that is a local path and does not exist is `missing`.
3. **Size** — under `--profile pod`: `README.md`, any `*/INDEX.md` and any root-level `.md` at 200
   lines; `ARCHITECTURE.md` at 300; everything else at 500. Under `--profile package`: the
   `--start` file at 300, everything else at 500. Over is `oversize`.
4. **Tracked** — every reached file must appear in `git ls-files`; absent is `untracked`. This is
   the check that catches the deny-by-default `.gitignore`, where a written root document is not
   yet a tracked one.
5. **`serves:`** — every reached file's frontmatter must carry a `serves:` field; absent is
   `no-serves`. Runs under `--profile pod` only — a skill package's files carry the skill's own
   frontmatter, not a pod document's.

The walk records depth alongside reachability: a file first reached deeper than 4 is `too-deep`.

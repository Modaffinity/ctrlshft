---
name: plan
description: "Use when an operator says \"plan <idea>\", \"plan this properly\", \"start a workstream\", \"carry this from idea to done\", or runs /plan inside a CortexOS pod. Not Claude Code's plan mode, and not superpowers:writing-plans. Not for: an in-session plan for the code change in front of you, executing a plan that already exists, or research without planning intent."
---

# Plan

## Overview

`plan` is the router for a fifteen-stage spine that carries one workstream from an idea to its
final documentation, across two sessions: an operator-led planning session (P1–P6, ending at a
handoff) and an unattended build session (B1–B9, an orchestrator dispatching stage subagents). This
file is a router, not a manual — it names every stage and every reference, carries the two loops
that hold the whole thing together, and sends you on to whichever reference has the rest.

The `description` above states triggers only, with no workflow summary: `writing-skills` measured
that a workflow summary in `description` becomes a shortcut agents take instead of reading the
skill, so it deliberately says only when to load this file, never what to do once it's loaded.

## When to use

Entry triggers, mirrored from `description`: an operator saying "plan <idea>", "plan this
properly", "start a workstream", "carry this from idea to done", or running `/plan` inside a
CortexOS pod.

Not for: an in-session plan for the code change in front of you — that's Claude Code plan mode or
`superpowers:writing-plans`, see the next section; executing a plan that already exists; or
research without planning intent — that's the `research` skill.

## Three things answer to "plan"

| Thing | What it is | How it is entered | Artifact |
|---|---|---|---|
| **Claude Code plan mode** | a harness mode — read-only, with an approval step | shift-tab | none; ephemeral |
| **`superpowers:writing-plans`** | writes one plan file from a spec | the spine invokes it at stage **Plan** | `plans/<slug>/<slug>-PLAN.md` |
| **`plan` (this skill)** | the whole pipeline, idea to documentation | "plan <idea>" in a pod | five tracked files under `plans/<slug>/` |

The spine runs inside plan mode or outside it. Entering plan mode never invokes the spine.

## The fifteen stages

| # | Stage | Trigger | Input | Output | Model | Exit condition |
|---|---|---|---|---|---|---|
| P1 | **Orient** | "plan <idea>" | the idea | branch `plan/<slug>`, `plans/<slug>/` created | — | `ARCHITECTURE.md`, `CONTEXT.md`, `README.md` and both `INDEX.md` files read and summarised to the operator in under twenty lines |
| P2 | **Frame** | "frame it" | the idea + P1 | a paragraph in chat | — | the operator agrees the problem statement is the one he meant |
| P3 | **Scan** | "scan for prior art" | P2 | `research/<topic>/` + its `research/INDEX.md` row | — | `research` skill's scan tier filed; index row added |
| P4 | **Grill** | "grill me on this" | P2, P3 | `CONTEXT.md` terms, `docs/adr/NNNN-*.md` | — | the operator stops the interview; every question answered or recorded as a Delegated decision |
| P5 | **Brief** | "write the brief" | P1–P4 | `plans/<slug>/BRIEF.md` | — | committed, tracked, and its clickable link given to the operator |
| P6 | **Handoff** | "hand off" | P5 | one paste-able prompt in chat | — | the prompt names the pod path, the branch, `BRIEF.md` and the read-pack |
| B1 | **Ground** | (the handoff) | `BRIEF.md` | `ARCHITECTURE.md` created or confirmed fresh | strong | the document exists, is under 300 lines, is tracked, and `README.md` links it |
| B2 | **Spec** | "write the spec" | `BRIEF.md` + read-pack | `plans/<slug>/SPEC.md` | strongest | brainstorming's Spec Self-Review passes; every open question the brief raised is settled |
| B3 | **Spec review** | "review the spec" | `SPEC.md` + packet | findings, returned | strong | a Codex round and a de-risk round have both run against the artifact's current version with no blocking finding open, or the cap reached and every residual ruled |
| B4 | **Plan** | "write the plan" | `SPEC.md` | `plans/<slug>/<slug>-PLAN.md` | strongest | `writing-plans`' Self-Review passes; no placeholder anywhere |
| B5 | **Plan review** | "review the plan" | the plan + packet | findings, returned | strong | same as B3 |
| B6 | **Implement** | "implement the plan" | the plan | commits on the workstream branch(es) | per SDD | every task in the plan has a commit and a passed task review |
| B7 | **Docs** | "run the docs stage" | the branch | `plans/<slug>/DOCS.md` + the files it changes | standard | all eight checklist items changed or confirmed with a reason |
| B8 | **Land** | "verify and land" | the branch | a merge commit, or a stop | standard | full verification passes **and** the merge is clean **and** the post-merge docs check passes; any one failing is a stop condition |
| B9 | **Report** | "report" | `STATE.md` | the report in chat; `plans/archive/<slug>/` | standard | report delivered, folder moved, `plans/INDEX.md` row moved |

P1–P6 in full: [PLANNING_SESSION.md](references/PLANNING_SESSION.md).
B1–B9 in full: [BUILD_SESSION.md](references/BUILD_SESSION.md).

## The between-stages loop, in brief

Seven steps, after every stage return: read the return; verify existence and content against disk;
branch on the verdict; write the ledger block; commit named paths only; confirm trackedness; dispatch
the next stage. Disk wins over the return, always — a `done` verdict disk disagrees with is treated
as `blocked`. Full procedure: [BUILD_SESSION.md](references/BUILD_SESSION.md).

## Resume, in brief

Six steps, for a fresh session with no memory: read `STATE.md`; read the frontmatter; verify the
claim against disk, never trust it; read `BRIEF.md`; read the last completed stage's artifact; run
the stage named in *Resume here*, reconciled against the disk check. Status is derived, never
declared. Full procedure: [BUILD_SESSION.md](references/BUILD_SESSION.md).

## The package

Seven files below are **v2** — written for the spine. Eleven are **v1-legacy**, kept unchanged
because a live v1 plan tree still depends on them; `/carve` enters them at
[V1_LEGACY.md](references/V1_LEGACY.md).

| File | Holds |
|---|---|
| `SKILL.md` (this file) | the eight sections above |
| [PLANNING_SESSION.md](references/PLANNING_SESSION.md) | The six stages · Rules the planning session carries · The handoff |
| [BUILD_SESSION.md](references/BUILD_SESSION.md) | The nine stages · Which superpowers skill each stage invokes · Why the plan file is named `<slug>-PLAN.md` · The between-stages loop · The orchestrator's commit, by output kind · Resume · Land, and the archive |
| [INTERFACES.md](references/INTERFACES.md) | Output kinds · The dispatch brief · The stage return · The revision dispatch · STATE.md · The Codex prompt · The de-risk dispatch |
| [REVIEW_ROUNDS.md](references/REVIEW_ROUNDS.md) | What a round is · Classifying a finding · The cap, and what happens at it · The advisor packet · Overflow · Cross-repo packets |
| [DOCS_STAGE.md](references/DOCS_STAGE.md) | The eight items · What item 8 fixes and what it records · The DOCS.md template · What docs-graph-check.py checks |
| [V1_LEGACY.md](references/V1_LEGACY.md) | v1's seven-step procedure; it links the nine v1 references |

| Entry point | Reaches |
|---|---|
| [V1_LEGACY.md](references/V1_LEGACY.md) | the nine v1 references (`FUNNEL.md`, `BOUNDARY_RITUAL.md`, `artifact-schema.md`, `coverage-taxonomy.md`, `dispatch-protocol.md`, `interview.md`, `persona-table.md`, `routing-table.md`, `sizing-factors.md`) and the two v1 scripts (`generate-plan-surface.py`, `check-plan-surface.sh`), all linked or named from inside it |

Two more scripts, `scripts/docs-graph-check.py` and `scripts/advisor-packet.py`, back this package's
checks and the review round's packet step — named here in backticks, not linked; the reachability
walk above follows `.md` only.

## Common mistakes

- **Loading `architect` for `/plan`.** `/plan` used to resolve to the `architect` skill — a recorded
  collision (aim leak 4) this release ends. `/plan` now resolves here.
- **Paraphrasing a template instead of copying it.** The dispatch brief, the stage return and
  `STATE.md`'s ledger block are copied verbatim — a paraphrase drifts from what the between-stages
  loop parses back out of it.
- **A stage subagent editing `STATE.md`.** Only the orchestrator writes the ledger, and only after
  verifying the stage's return against disk. A subagent that edits it directly can record `done`
  disk never confirmed.
- **Buying a fourth review round.** The cap is three rounds, no more. A fourth round is a stop
  condition, not a retry — see [the cap](references/REVIEW_ROUNDS.md).
- **`git add -A` in a repo carrying another surface's work.** `~/dotfiles` carries another surface's
  uncommitted work on `main`. Every commit here stages named paths only.

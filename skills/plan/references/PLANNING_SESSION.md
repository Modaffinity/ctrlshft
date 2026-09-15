# Planning session — stages P1–P6

Operator-led. Ends at the brief. Six stages, one session; the build session (`BUILD_SESSION.md`)
starts only after P6 hands off.

## The six stages

| # | Stage | Trigger | Input | Output | Exit condition |
|---|---|---|---|---|---|
| P1 | **Orient** | "plan <idea>" | the idea | branch `plan/<slug>`, `plans/<slug>/` created | `ARCHITECTURE.md`, `CONTEXT.md`, `README.md`, `plans/INDEX.md`, `research/INDEX.md` read and summarised back to the operator in under twenty lines |
| P2 | **Frame** | "frame it" | the idea + P1 | a paragraph in chat | the operator agrees the problem statement is the one he meant |
| P3 | **Scan** | "scan for prior art" | P2 | `research/<topic>/` + its `research/INDEX.md` row | `research` skill's scan tier filed; index row added |
| P4 | **Grill** | "grill me on this" | P2, P3 | `CONTEXT.md` terms, `docs/adr/NNNN-*.md` | the operator stops the interview; every question answered or recorded as a Delegated decision |
| P5 | **Brief** | "write the brief" | P1–P4 | `plans/<slug>/BRIEF.md` | committed, tracked, and its clickable link given to the operator |
| P6 | **Handoff** | "hand off" | P5 | one paste-able prompt in chat | the prompt names the pod path, the branch, `BRIEF.md` and the read-pack |

### P1 — Orient

- **reads:** `ARCHITECTURE.md`, `CONTEXT.md`, `README.md`, `plans/INDEX.md`, `research/INDEX.md`.
- **writes:** branch `plan/<slug>`; `plans/<slug>/` created.
- **must not:** propose a design.

### P2 — Frame

- **reads:** the idea; P1's output.
- **writes:** nothing on disk — a paragraph in chat, and no more.
- **must not:** write a file.

### P3 — Scan

- **reads:** P2's agreed problem statement.
- **writes:** `research/<topic>/`, plus its row in `research/INDEX.md`.
- **must not:** inline the research into the brief; must not use the installed `research` skill's
  own `context/research/<topic>/` output path — see the path-override rule below.

### P4 — Grill

- **reads:** P2, P3.
- **writes:** `CONTEXT.md` terms; `docs/adr/NNNN-*.md`.
- **must not:** use the option picker; must not invoke superpowers `brainstorming`.

### P5 — Brief

- **reads:** P1 through P4.
- **writes:** `plans/<slug>/BRIEF.md`, committed and tracked.
- **must not:** leave the brief untracked.

**The brief ships one dial line.** *Timidity is as bad as recklessness*, and both extremes are
forbidden: the more load-bearing or dangerous the work, the further toward caution; the less, the
further toward boldness — a **range**, never an endpoint. P5 writes that position into the brief in
one line with its reason, in this form:

```
**Dial:** <position, in a phrase> — <the reason, naming what makes this work load-bearing or not>
```

A brief is **approved, not frozen**, so no gate can ever fire on this line — which is precisely why
its shape is fixed here, at the stage that decides what a brief contains, instead of being left to
whoever writes one. The plan that follows inherits the position, and there the freeze gate does
check that the line exists.

### P6 — Handoff

- **reads:** P5's committed, tracked brief.
- **writes:** one paste-able prompt, in chat only — nothing on disk.
- **must not:** start the build session.

**Across all six stages, one more rule holds:** a stage stays inside the pod. A cross-pod question is
the operator's to answer, or for the stage to declare unanswerable — never a stage's to go and read.

## Rules the planning session carries

**Rules it carries.** The Grill is the only interview — `grill-with-docs`, in plain chat, never the
option picker; every question offers a "you decide" option, recorded in the brief as a Delegated
decision with its reasoning. Superpowers brainstorming is **not** invoked here.

⚠️ **P3 overrides the installed `research` skill's output path.** That skill files to
`context/research/<topic>/` and regenerates its index with
`bash scripts/build-index.sh context/research`. A CortexOS pod files to `research/<topic>/`
(`research/CLAUDE.md`, and `ARCHITECTURE.md`'s conventions), so P3's
dispatch states the pod's path explicitly, says that the skill's own default differs, and passes
`research` as the root argument to both `build-index.sh` and `check-surface.sh`. The target pod's
convention wins; a spine that inherited the skill's default would file every workstream's prior-art
scan where the pod's index cannot reach it.

**Commit at P5 only, not P3 and P4.** The brief's "commit per stage" rule is implemented for P5
alone. The planning session is operator-led and live — an uncommitted intermediate from P3 (scan) or
P4 (grill) stays visible to the human in the room — while the build session's stages are the ones
that must survive a lost context, so every B-stage gets its own commit and P3/P4 do not. Cost if
wrong: a planning session that dies mid-P3 or mid-P4 loses uncommitted work the operator would redo
by hand; accepted because a live operator is present to notice and re-run the stage, unlike the
unattended build session.

## The handoff

P6's exit condition — "the prompt names the pod path, the branch, `BRIEF.md` and the read-pack" —
expands to four required slots. A handoff prompt missing any one of these is not a handoff:

- The **absolute pod path**.
- The **branch name**.
- The path to **`plans/<slug>/BRIEF.md`**.
- The **read-pack** — a numbered list of exact paths, no globs.

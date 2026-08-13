---
name: plan
description: "Turn a vague idea into dispatchable CortexOS goals. Interviews, researches, decomposes into a vision → branches → goals structure, emits bounded work packets with proven definitions of done, and hands off dispatch commands for the operator to run. Use for: plan a project, break this down, what should we build first, decompose this into tasks. Not for: executing goals (that is CortexOS), adapting mid-flight (that is the operating model's §9), or research without planning intent (that is research)."
---

# Plan

Output "Read Plan skill." to chat to acknowledge you read this file.

**Position in the pair.** `research` produces the corpus; `plan` consumes it and emits dispatchable work.
The skill never dispatches — it emits text the operator runs.

## Mode routing

| Mode | Trigger | Entry point |
|---|---|---|
| **New plan** | "Plan …", "break this down", a bare idea with no existing plan directory | Step 1 (Discovery) |
| **Resume** | An existing plan directory is named, or `context/plans/<slug>/` exists | Step 0 (Resume) |

---

## Step 0 — Resume

When invoked against an existing plan directory:

1. Read `.plan.yaml` and `INDEX.md`.
2. Report to the operator:
   - The vision.
   - Each branch and its status (sketched / detailed).
   - The open waves — which branches are currently being detailed, up to the cap, or that none are
     open.
   - Each goal and its status (emitted / gate-1-passed / gate-2-passed / skipped), including verdicts.
   - Any falsified assumptions (from `assumptions.md` or `log.jsonl`).
   - Any open questions (from `questions.md`).
   - **What is next** — which wave(s) to open next within the cap, which branch(es) to detail, or
     that the plan is complete.
3. Wait for the operator's instruction before acting.

Do not re-run discovery or re-emit goals that already exist. Resume means *read and report*, then
take direction.

---

## Step 1 — Discovery loop

**The loop owns its interview.** It calls `research` for grounding; it does not call an external
interviewer. `grill-me`'s discipline is adopted as text in the Attack posture (1b.3).

### 1a. Scope check

Before any detailed questioning, assess scope:

> If the request describes multiple independent subsystems, **do not spend questions refining details
> of a project that needs to be decomposed first.** Flag it, help the operator see the independent
> pieces, and proceed to decompose at vision level.

### 1b. Three postures, in order

The interview proceeds through three sequential postures:

1. **Build** — generate the vision. Run the coverage taxonomy, propose approaches, synthesise a
   design from the operator's answers. Constructive and additive.
2. **Complete** — fill gaps. Scan the emerging vision for underspecification: ambiguous adjectives
   lacking quantification, missing completion signals, undefined terms. Encode answers back.
3. **Attack** — stress-test before committing to decomposition. Apply `grill-me`'s discipline:
   sharpen fuzzy language, invent concrete boundary scenarios, cross-reference against the repo.

### 1c. Coverage taxonomy

Run a structured coverage scan during the Build posture. For each category, mark
**Clear / Partial / Missing** and use the map to decide what to ask:

1. Functional scope and behaviour
2. Domain and data model
3. Interaction and UX flow
4. Non-functional quality attributes
5. Integration and external dependencies
6. Edge cases and failure handling
7. Constraints and tradeoffs
8. Terminology and consistency
9. Completion signals (acceptance-criteria testability, measurable definition-of-done)
10. Stakeholders, owners, and approval paths
11. Existing assets, prior art, and constraints from the repo

Full taxonomy with examples and filtering rules: `references/coverage-taxonomy.md`.

### 1d. Capped questions

Generate questions **internally** from the coverage scan. Rules:

- **Hard cap: 8 questions per round.** Each must be answerable by 2–5 option multiple choice or a
  short answer. Ranked by **Impact x Uncertainty** when more than 8 categories are unresolved.
- Include a **pre-filled recommended answer** for every question.
- Ask **one question at a time**, wait for the answer.
- Exclude questions whose answer would not materially change the decomposition, the definition of
  done, or the wave order.
- Never reveal queued questions in advance.
- Stop early when critical ambiguities are resolved or the operator says done.

### 1e. Write-back

Every answered question is immediately written into the plan artifact. **Write-back means
appending the corresponding event to `log.jsonl`** — `decision-made`, `assumption-recorded` or
`question-opened` — **and regenerating** with `scripts/generate-plan-surface.py`. The registers
(`decisions.md`, `assumptions.md`, `questions.md`) are how the answer *surfaces*; they are
generated, never written by hand. An interview whose output lives only in the transcript is lost
at session end.

### 1f. Research interleave

When a question exposes an ungrounded assumption or a claim that cannot be verified from available
context, **call `research`** (do not research inline). Record the assumption with its provenance
and confidence. Re-enter the interview after research returns.

An assumption that cannot be grounded is recorded with `confidence: low` and its dependents are
listed. **Stop or flag** dependent work rather than proceeding as though the assumption were true.
Do not invent evidence or fabricate a grounding source.

### 1g. Understanding before decomposition

**Decompose too early and you decompose the wrong object** — an armchair sliced as though it were a
car. Grill at **vision level** until the whole is understood well enough that **the carve would be
right**, then carve. Detail within a branch waits for that branch's wave.

The stopping rule is not "everything is known" but **"the carve would be right."** Both failure
modes are real and opposite:
- Too shallow: the decomposition is wrong — branches that do not correspond to real seams.
- Too deep: questions spent refining detail inside branches that have not been carved yet.

When the vision is grounded and the branch map would be sound, proceed to Step 2.

---

## Step 2 — Vision and branch map

**This is a selection, not the whole vision** — when the corpus is larger than one version should
carry, choosing the branch map is the funnel's job: the four questions, gate zero, and the value
floor, run at every version boundary. Full procedure: `references/FUNNEL.md` (a synced copy — the
canonical version lives at `docs/vision/FUNNEL.md` in the `plan-skill` pod, gitignored there).

Produce:

1. **The vision statement** — what this project achieves, in a paragraph. Write it to `direction.md`.
2. **The branch map** — every branch named and sketched (one or two sentences each). Sketched means
   scoped but not decomposed into goals.
3. **The assumption register** — each assumption with provenance, confidence, and the list of goals
   or branches that depend on it. Record via `assumption-recorded` events; `assumptions.md` is
   generated from them.
4. **The decision register** — each decision with why and **implications** (stating consequences at
   decision time is what makes a register usable months later). Record via `decision-made` events;
   `decisions.md` is generated from them.
5. **Open questions** — each with what would resolve it. Record via `question-opened` events;
   `questions.md` is generated from them.

**Appending to `log.jsonl` is the only write path.** `direction.md` is the one hand-written file;
every register is regenerated. Append:
- `vision-set` — once, with the vision title and summary.
- `branch-sketched` — once per branch, with slug, name, and summary.
- `funnel-run` — once, when the funnel selects this version's scope, with what was selected and
  what was deferred.
- `decision-made` — for each decision, with id, title, why, and implications.
- `assumption-recorded` — for each assumption, with id, text, provenance, confidence, dependents.
- `question-opened` — for each open question, with id, text, and resolves_when.

### Operator gate (the only full gate)

Present the vision and branch map to the operator. **Stop and wait for approval.** Do not proceed
to wave detailing until the operator approves. Log: `gate-passed` with `gate: vision-approval`.

This is the single operator gate. After this, each wave gets a light checkpoint (Step 3), and
**nothing interrupts inside a wave.**

---

## Step 3 — Wave detailing

### 3a. Wave ordering

Order branches by **risk**: highest dependents x lowest confidence first. The assumption register
carries the data — the branch whose assumptions are most depended-on and least confident goes first,
so whatever could break everything gets tested first.

### 3b. Open the wave

Select the next branch by risk order. Log: `wave-opened` with wave_id and branch slug.

**Up to two waves may be open at once — branches progress in parallel, not one at a time.** The cap
bounds attention, not dependency order, and the operator may raise it. Refuse requests to open a
wave beyond the cap. Branches beyond the cap remain sketched until a wave slot opens.

### 3c. Detail the branch

Decompose the branch into goals. Log: `branch-detailed` with the branch slug.

For each goal, apply the five sizing factors in precedence order (Step 4) and emit it (Step 5).

### 3d. Light checkpoint

After all goals in the wave are emitted, present the wave summary to the operator. This is a
**light checkpoint**, not a gate — the operator sees what was produced and can redirect, but the
default is to proceed to dispatch handoff.

### 3e. Close the wave

After dispatch handoff (Step 6), log: `wave-closed` with wave_id.

If a goal is **skipped** (will not proceed, downstream must stop waiting), log: `goal-skipped` with
goal_id, branch, and reason. This is distinct from blocked — blocked means *cannot proceed yet*;
skipped means *will not proceed*. Nothing changes in CortexOS: a goal skipped after dispatch maps
to the bus's existing `cancelled`.

If more branches remain, return to Step 3a to open the next wave — under the cap, it can run
alongside waves still open. Each wave benefits from what was learned in prior closed waves rather
than guesses made earlier.

When no branches remain, this version is done — that is the **version boundary**. Before the next
version is scoped with the funnel above, run the boundary ritual: the adversarial review, the
deferral walk, reconciliation, and the value-floor test. Full procedure:
`references/BOUNDARY_RITUAL.md` (a synced copy — the canonical version lives at
`docs/vision/BOUNDARY_RITUAL.md` in the `plan-skill` pod, gitignored there).

---

## Step 4 — Sizing a goal

**Five factors draw the boundary. Context budget is not one of them** — it is the check applied
afterwards. Size-driven carving produces goals cut at arbitrary byte boundaries.

| # | Factor | Rule |
|---|---|---|
| 1 | **Outcome coherence** | One deliverable — one thing that is *finished*. Primary; the others refine it |
| 2 | **Kind of work** | Research, implement, review, judge are different kinds needing different agents. *"Research this then build it"* is **two goals however small** |
| 3 | **Ownership** | Research and paid calls are `research-agent`, exclusive. Work spanning two owners is **two goals even when tiny** — ownership beats size |
| 4 | **Verification boundary** | One goal, one definition of done, one proving command. Two unrelated proving commands means two goals |
| 5 | **Relationship** | Work that must succeed or fail together is not split. Work where A must verify before B has its seam there |

### Budget check (applied after the five factors)

| Bound | Context bundle | Whole-loop | Meaning |
|---|---|---|---|
| **Floor** | — | **20K tokens** | Below this, merge it — **unless merging would cross an ownership or kind boundary**. Ownership and kind beat size; a tiny goal that cannot legally merge stands as-is |
| **Default** | ≤ 40K tokens (~150 KB) | ~64K | One deliverable, several files |
| **Ceiling** | 80K | ~128K | Needs a named seam; signal the branch may be carved too coarse |

Over the ceiling, look for a natural seam — another outcome hiding inside. If there genuinely is
none, **read less rather than split**: tighter pointers, an index instead of whole files.

All three numbers are starting values, **revisable from run records**. The floor is revisable too —
it is a heuristic with a documented origin, not a mechanism active in our runtime.

**Never a list of 2-5 minute steps.** Writing the agent's steps removes the reason to use an agent.

**Every goal must have stop conditions.** An objective with no stop is how an agent grinds or
fabricates.

Sizing factor details and worked examples: `references/sizing-factors.md`.

---

## Step 5 — Goal emission

Emit each goal with exactly **five fields**:

### Direction

The outcome, its stop conditions, and how it is proven. Includes:
- The **gate-1 proving command**: not "file X exists and contains Y" but "file X, produced by
  running Z, with this exit code." A stub file satisfies an artifact check; it cannot satisfy a
  command's fresh output.
- Where a **judged gate** (gate 2) applies: the criteria, golden examples, and named judge — all
  written at plan time, never after seeing the output.

A definition of done with no proving command is rejected. Rewrite it until it names the command.

### Output format

What the deliverable must look like — stated in the brief, not left to the definition of done.
Three descriptions, three jobs, no overlap: the **output format** says what shape it takes (*before*);
the **definition of done** proves it was produced (*after*); the **judged criteria** assess whether
it is good (*after*).

### Context

Exact file paths as **pointers, never copies**, resolved at plan time using index-guided selection:
read the index, match entries against this goal's purpose, include what is relevant. The worker
never browses.

State which kind of grounding applies per source: third-party claims, source, internal record, or
measured.

### Guardrails

What is out of bounds, loop limits, cost ceiling, context budget (from Step 4), and the **autonomy
class** from the operating model. The autonomy class is a declared permission envelope for
unattended action — it lives here. Autonomy as latitude is not a field; it is the space the other
other fields leave.

### Unlocks

Which goals this one releases when it completes — the **forward edge**. The assumption register
carries backward edges (what breaks if this is wrong); Unlocks answers *what does finishing this
make possible*, which is the question wave ordering actually asks.

Maps directly to CortexOS's `--blocks` parameter at dispatch.

Log: `goal-emitted` with goal_id, branch, title, and wave. The emitted goal is an **outcome, not a
recipe** — it describes what should exist when done, not a numbered list of steps for the agent.

---

## Step 6 — Dispatch handoff

After all goals in the wave are emitted, produce the dispatch block. The skill **never dispatches**
— it emits text for the operator to run.

### 6a. Bus-task-first commands

For each goal, emit the CortexOS dispatch commands. **This is the whole form — copy it, do not
paraphrase it.** Full detail and the failure modes: `references/dispatch-protocol.md`.

```
docker exec cortexos-main bash -lc '
CTX_ORG=<org> cortextos bus create-task "<goal title>" \
  --project <pod> \
  --assignee <worker-name> \
  --desc "Packet: <pod-relative packet path>"'

docker exec cortexos-main bash -lc '
CTX_ORG=<org> cortextos spawn-worker <worker-name> \
  --dir /home/node/.cortextos/default/pods/<pod> \
  --prompt "CortexOS task id: <id>. Read AGENTS.md and the task packet at <path>, then do the task."'
```

**Six things that are wrong in the obvious guess, and the two that fail *silently*:**

| | Correct |
|---|---|
| Binary | **`cortextos`**, not `cortexos`. `cortexos` is ours, `cortextos` is upstream's — this is `OL-57` and it recurs |
| Subcommand | **`bus create-task`** — not top-level |
| Title | **positional** — there is no `--title` flag |
| Packet | no `--packet` flag exists. Put the path in **`--desc`**; the worker reaches it via the prompt |
| Worker name | **required positional** on `spawn-worker` |
| `--dir` | the **resolved container path**, `/home/node/.cortextos/default/pods/<pod>` |

- ⚠️ **`CTX_ORG` selects the task store at create time.** Omit or mistake it and the task lands
  somewhere the executing agent cannot complete it — the bus-completion gap, and it looks like
  success. A pod under `hq/` does **not** have org `hq`; use the registered runtime org id.
- ⚠️ **`--assignee` must be set and must match the worker's bus identity**, or nothing connects the
  task to who runs it. The bus accepts any free text here and never validates it.

**The task id travels in the worker prompt, never as a flag.** `spawn-worker` has no `--task` option
and creates no dashboard-visible task.

**Write the prompt to point at the task** — *"read `AGENTS.md` and the packet at X, then do the
task."* A prompt that asserts identity or authority (*"you are X, now do Y"*) is refused as
prompt-injection, correctly, because from inside a PTY it is indistinguishable from one.

**`unlocks` does NOT map to `--blocks` at emission time.** `--blocks` takes comma-separated **task
IDs**, and an unlocked goal has no task yet. Creating one so it can be pointed at breaks the rule
that the bus is executable-only and the board is the queue — a pending task nobody can start is
exactly the future-task noise that rule forbids. Keep the intent in `--desc`, and wire the edge the
other way when the downstream goal is actually dispatched: **`--blocked-by <upstream-task-id>`**.

### 6b. Dependency edges

State the dependency graph explicitly. Which goals block which. The operator can verify the edges
before dispatching.

### 6c. Gap list

List anything the plan identified that is needed but not yet available: missing context files,
unresolved questions, assumptions needing verification, external dependencies. Each gap names what
would resolve it.

### 6d. Reliable-task requirements

Every emitted goal inherits from `reliable-task` as hard requirements:
- A bounded read-set resolved before dispatch (never send a worker to search).
- Incremental checkpointing, never one final commit.
- A machine-checkable definition of done written before dispatch.
- Workers produce and commit but never set status.

### 6e. Lane choice

Offer the operator a choice this skill has not asked before: **light** or **heavy**, with a
recommended default (Step 1d's rule). **Heavy** means every goal in this wave gets a gate-2 judged
review before being called done — a fresh reviewer per task, the rigor `subagent-driven-development`
applies. **Light** means gate-1 mechanical verification is enough; no judged review is expected.
Neither is free: heavy costs a reviewer dispatch per goal, light accepts more risk of an unnoticed
defect clearing gate 1 alone.

**Record the choice — it does not live only in the transcript.** Append a `lane` change record to
`vision/changes/`: `id` (its own field, distinct from the filename — the worked example's is
`ch-20260812-lane-heavy`); `subject` is the coordination point for the version being planned, or
the specific scope item this choice narrows to; `dimension: lane`; `from_ref` is `none` on the
first choice for that subject, or the prior lane otherwise; `to_ref` is `light` or `heavy`; plus
`effective_at` and `reason`. Write-once and sealed, like every `vision/changes/` record — shape:
`vision/changes/20260812T1900-lane-heavy-for-finish-v1.md`. Log `lane-chosen` to `log.jsonl` with
the same subject and lane, so the plan's own record carries the choice too.

---

## Step 7 — Artifact structure

All plan artifacts live in `context/plans/<vision-slug>/`. The append-only log is the source of
truth; the readable tree is generated from it.

```
context/plans/<vision-slug>/
  .plan.yaml        # machine-readable state (generated)
  INDEX.md           # branch map, status, goals (generated)
  direction.md       # hand-written — the vision
  decisions.md       # generated — dated register: Decision, Why, Implications
  assumptions.md     # generated — each with provenance, confidence, dependents
  questions.md       # generated — open, with what would resolve each
  log.jsonl          # append-only source of truth
  branches/NN-<slug>/   # sketched or detailed; goals live here when detailed
```

Nothing in the generated tree is hand-edited. A change is an append to `log.jsonl`, never an edit
to a generated file.

**Required guard:** regeneration-is-a-no-op — `check-plan-surface.sh` must show no diff between
`log.jsonl` and the generated files.

### Event vocabulary (17 events — 15 fixed before build, 2 added by Task 7)

**Extended, not silently patched.** The 15 below were fixed before build. Two more are added here
because Step 2's funnel reference and Step 6's lane offer are decisions like any other this skill
makes — write-back applies to them too, or they live only in the transcript. Extending the
vocabulary is a deliberate, stated act; overloading an existing event instead would have made
`log.jsonl` unparseable without external context.

| Event | When logged |
|---|---|
| `vision-set` | Vision statement is written |
| `branch-sketched` | A branch is named and scoped |
| `branch-detailed` | A branch is decomposed into goals |
| `wave-opened` | A wave begins on a branch |
| `wave-closed` | A wave completes |
| `goal-emitted` | A goal is produced with all five fields |
| `goal-skipped` | A goal will not proceed; downstream stops waiting |
| `decision-made` | A decision is recorded with implications |
| `assumption-recorded` | An assumption is logged with provenance and confidence |
| `assumption-falsified` | An assumption proved wrong; dependents are flagged |
| `question-opened` | A question is raised with its resolution condition |
| `question-resolved` | A question is answered |
| `gate-passed` | An approval gate is cleared |
| `verdict-recorded` | A gate-2 judge writes a verdict |
| `run-record-written` | A run record captures actuals for a completed goal |
| `lane-chosen` | The operator picks light or heavy at dispatch handoff (Step 6e) |
| `funnel-run` | The funnel (`references/FUNNEL.md`) is applied to select this version's scope (Step 2) |

---

## Verification — two gates, in order

**Gate 1, mechanical.** `verify_task.py` checks the definition of done against disk and git. Path
resolved at dispatch time and recorded in the run report:
`python3 <lab>/skills/reliable-task/verify_task.py --pod <pod> --dod <dod.json>`.
**`watch_task.py` is the continuous guard** — it re-derives status every interval and reverts a
worker-declared completion that disk does not support. Running it for the life of a dispatch is not
optional.

**Gate 2, judged.** An independent agent — a different model from the producer — assesses the
deliverable against criteria and golden examples written at plan time. Runs only if gate 1 passes.
Writes a `verdict-recorded` artifact that gate 1 then checks for. The judge never sets status
directly. In v1, the judge is dispatched by the operator, by hand.

**The run record.** After verification, the **operator** writes the run record by appending
`run-record-written` to `log.jsonl` — capturing what the goal actually read, which assumptions
proved false, and whether it completed without prescribed steps. This happens **by default for
every completed goal, not on request**: the sizing numbers in Step 4 are revised from these
records, and learn-from-use has no other input. Like the judge dispatch, this is a stated
obligation in v1, not a mechanism.

---

## Boundaries

### In scope
- Discovery, decomposition, goal emission, dispatch handoff, resume — for **one project at a time**.
- Calling `research` for grounding. Owning the interview.
- Writing the plan artifact to `context/plans/`.

### Out of scope — do not implement
- **Automatic plan repair** — record that an assumption failed; a human re-runs wave detailing.
- **Delta-based change folders** — v1 mutation is human-mediated at wave checkpoints.
- **The routing layer** — v1 emits requirements; a table resolves them to agent and model by hand.
- **A persona system** — v1 is a table of prompt preambles by task kind.
- **Rollback as automated action** — named as an option; executed by the operator.
- **Cross-project planning** — one project at a time.
- **Brownfield entry** — v1 starts from an idea only; no adopting existing plan documents.
- **Dispatching** — the skill never dispatches. It emits commands as text.

### Hard constraints
- The plan artifact is the **single source of truth**. Status is derived from disk, never declared.
- Context is **pointers, never copies** — no file content is inlined into goals.
- The operator gate (Step 2) is the **only full gate**. Wave checkpoints are light.
- **Nothing interrupts inside a wave.**
- Goals are **outcomes, not recipes** — no prescribed steps.
- The **event vocabulary is fixed by default** — all mutations go through `log.jsonl` as typed
  events; extending it is a deliberate, stated act (Step 7's vocabulary table), never a silent
  patch.

## Reference files (Slice 5)

| File | Contains |
|---|---|
| `references/coverage-taxonomy.md` | Full coverage taxonomy with examples and filtering rules |
| `references/sizing-factors.md` | Sizing factor details and worked examples |
| `references/interview.md` | Interview discipline rules, the three postures, and question-design rules |
| `references/dispatch-protocol.md` | Bus-task-first protocol detail and command templates |
| `references/artifact-schema.md` | Full `.plan.yaml` schema and `log.jsonl` event schemas |
| `references/routing-table.md` | Requirement → owning specialist → worker model lookup (dispatch-time) |
| `references/persona-table.md` | Prompt preambles by task kind, with "when not to use it" conditions |

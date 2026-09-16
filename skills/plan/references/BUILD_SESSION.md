# Build session — stages B1–B9

The build session picks up where the planning session's handoff (P6) ends. Orchestrator-run — no
operator input — until B9's report or a `stop` verdict.

## The nine stages

| # | Stage | Trigger | Input | Output | Model | Exit condition |
|---|---|---|---|---|---|---|
| B1 | **Ground** | (the handoff) | `BRIEF.md` | `ARCHITECTURE.md` created or confirmed fresh | standard | the document exists, is under 300 lines, is tracked, and `README.md` links it · both seat-gauge readings are in the first ledger block · [B1's procedure](GROUND_STAGE.md) |
| B2 | **Spec** | "write the spec" | `BRIEF.md` + read-pack | `plans/<slug>/SPEC.md` | strongest | brainstorming's Spec Self-Review passes; every open question the brief raised is settled |
| B3 | **Spec review** | "review the spec" | `SPEC.md` + packet | findings, returned | standard · strongest | a [Codex round](INTERFACES.md#the-codex-prompt) and a [de-risk round](INTERFACES.md#the-de-risk-dispatch) have both run against the artifact's current version with no blocking finding open, or the cap reached and every residual ruled |
| B4 | **Plan** | "write the plan" | `SPEC.md` | `plans/<slug>/<slug>-PLAN.md` | strongest | `writing-plans`' Self-Review passes; no placeholder anywhere · [what a plan step carries](#what-a-plan-step-carries) · every acceptance check it writes follows [CHECKS.md](CHECKS.md) |
| B5 | **Plan review** | "review the plan" | the plan + packet | findings, returned | standard · strongest | same as B3 |
| B6 | **Implement** | "implement the plan" | the plan | commits on the workstream branch(es) | strongest · per SDD | every task in the plan has a commit and a passed task review · every check it runs follows [CHECKS.md](CHECKS.md) |
| B7 | **Docs** | "run the docs stage" | the branch | `plans/<slug>/DOCS.md` + the files it changes | standard | all eight checklist items changed or confirmed with a reason |
| B8 | **Land** | "verify and land" | the branch | a merge commit, or a stop | standard | full verification passes **and** the merge is clean **and** the post-merge docs check passes; any one failing is a stop condition · its gates follow [CHECKS.md](CHECKS.md) |
| B9 | **Report** | "report" | `STATE.md` | the report in chat; `plans/archive/<slug>/` | standard | report delivered, folder moved, `plans/INDEX.md` row moved |

**B1 also reads the meter.** A build session reads the seat gauge at session start —
`~/dotfiles/skills/plan/scripts/seat-gauge.py` — and applies the band it prints, recording
`unknown` when `rate_limits` is not yet populated. An `unknown` start reading is the expected shape
of a reading taken before the harness's first API response, **not** a licence to skip it: the
brief is the controlling document and it says the session reads the odometer at start and applies
the band. The session then **re-reads at the first stage boundary**, and **both** readings go in the
first ledger block, so the band the run actually routed on is readable from the record rather than
asserted afterwards.

## Which superpowers skill each stage invokes

B2 → `brainstorming`, architectural path, questions and Visual Companion skipped. B4 →
`writing-plans`. B6 → `subagent-driven-development`, with `test-driven-development` inline where the
deliverable is code. B8 → `verification-before-completion` then `finishing-a-development-branch`. B1,
B3, B5 and B7 invoke none — they are the four pieces the plugin does not have (architecture as a
phase, a second-model round, a pre-spec de-risk, a closing docs stage). B9 is bookkeeping.

⚠️ **Naming note:** this bootstrap run's `STATE.md` predates the table above and numbers its stages
1–8, folding plan review into stage 4: 1→B1, 2→B2, 3→B3, 4→B4+B5, 5→B6, 6→B7, 7→B8, 8→B9. Nothing
renumbers a run in flight.

Every one of these skills expects a human to answer its own gates — `writing-plans`' Self-Review,
brainstorming's Spec Self-Review, `verification-before-completion`'s checks. A stage subagent answers
them itself; that instruction, and the operator authorization behind it, live once in
[the dispatch brief](INTERFACES.md#the-dispatch-brief)'s *Your gates* field and are not restated here.

## Choosing the model

**Three tiers, mapped once** to what this harness actually offers:

| Tier | This harness | Measured in use |
|---|---|---|
| `cheap` | `haiku` | this stage's two probe dispatches, `.meta.json` `"model":"haiku"` |
| `standard` | `sonnet` | B1 Ground, `.meta.json` `"model":"sonnet"` |
| `strongest` | `opus` | B2 Spec, `.meta.json` `"model":"opus"` |

The Agent tool also offers `fable`. It is **not** assigned a tier, because this run has not measured
it and naming a model without measuring it is exactly the assumption `C9` forbids.

**The rule, as it ships:**

**Name the model in every dispatch.** An omitted model inherits the orchestrator's, which is the
most expensive one — `subagent-driven-development/SKILL.md` says so and this spine depends on it.
**The verb test.** *"Apply this specified list"* or *"run these and report"* → `cheap`. *"Decide"*,
*"design"*, *"find what is wrong"* → `strongest`. Everything between → `standard`. **On real
doubt, go bigger.**
**The triad.** Every plan optimises quality, token consumption and time **together**, in that
general order and held **marginally, never lexically** — *"for a little extra quality, a trillion
tokens is an absolute no."* Naming two while sheltering the third is the failure mode this guards
against, and it is why the order is a tie-breaker rather than a ranking: going bigger is right when
the doubt is real and wrong when it buys a rounding error at three times the spend and twice the
wall clock.
**Turn count beats token price** (SDD's measurement, cited not restated): a cheaper model that
takes three times the turns costs more. A tier is a floor, not a target.

**The assignment for this spine:**

| Stage or step | Tier | Why |
|---|---|---|
| B1 Ground | `standard` | applies a specified procedure — `GROUND_STAGE.md` makes it mechanical |
| B2 Spec | `strongest` | decide and design; the brief names it |
| B3/B5 Coverage pass | `standard` | *finds what is absent* — a list walk with judgement at each row |
| B3/B5 Codex round | `standard` | assembles a packet, calls the official Codex plugin (`codex-companion.mjs task`), transcribes findings; Codex does the reasoning |
| B3/B5 de-risk round | `strongest` | designs falsifying experiments; the brief names it |
| B4 Plan | `strongest` | the brief names it |
| B6 controller | `strongest` | dispatches, judges reports, rules |
| B6 implementers and reviewers | per SDD | SDD's own table, cited |
| B6 final whole-branch review | `strongest` | the brief names it |
| B7 Docs · B8 Land · B9 Report | `standard` | specified checklists and named gates |
| the spend-accounting step | `cheap` | runs a script and reports its output |

**Per-task model choice inside B6 is not restated here** — it is `subagent-driven-development`'s own,
at `subagent-driven-development/SKILL.md` lines 186–218 of superpowers 6.3.0, and this section cites
it by file and line rather than copying it.

### The dial

**Timidity is as bad as recklessness**, and both extremes are forbidden. The more load-bearing or
dangerous the work, the further toward caution; the less, the further toward boldness — a **range**,
never an endpoint. A session that gates every step behind an operator it cannot reach has failed in
the same way as one that resolves a merge conflict on its own judgement; only the direction differs.

**Every brief and plan states its dial position in one line, with the reason:**

```
**Dial:** <position, in a phrase> — <the reason, naming what makes this work load-bearing or not>
```

The freeze gate checks that the line **exists** — presence is mechanical, the judgement stays with
the author. A brief is approved rather than frozen, so no gate fires on a brief's line; it is
written anyway, because the plan that follows inherits the position it sets.

### The context ceiling (`C6`)

Three bands, read against the orchestrator's own context at each stage boundary:

| Context at the boundary | Action | Provenance |
|---|---|---|
| under 250,000 | nothing | measured this run: a heavy artifact-writing stage peaked at 148,233 |
| 250,000 – 500,000 | a **blocking** Finding on the *next* stage's ledger block, closed by handing over by file instead of by paste, or by a Ruling naming what made it necessary | headroom above the observed heavy case, well below the failure |
| over 500,000 | `stop` — the run is reproducing release 1's failure and spending the allowance to do it | release 1's controller reached **829k** |

The thresholds are a first calibration from two measurements, and the run reports its actual figures
so a later release can tighten them with data rather than with judgement.

**Runnable check:** `stage-spend.py --orchestrator <session-id>` (Task 11).

**And the rule that makes the ceiling achievable**, restated locally because a rule that depends on
another skill staying loaded is not enforced:

**The orchestrator never pastes a file's content into a dispatch; it names the path.** Context is
pointers, never copies — a copy goes stale silently and a pointer cannot. A stage return is short
by template; the artifact carries the detail.

## Why the plan file is named `<slug>-PLAN.md`

`subagent-driven-development` resolves its scratch workspace with `scripts/sdd-workspace PLAN_FILE`,
which computes `slug=$(basename "$plan" .md)` and creates `<repo-root>/.superpowers/sdd/<slug>/`.
**There is no override**: the name is computed by a shell script from the path it is handed, and
SDD's `SKILL.md` exposes no workspace-name parameter — verified at source in superpowers 6.3.0. So a
canonical `PLAN.md` would put *every* workstream in `.superpowers/sdd/PLAN/`, defeating the per-plan
isolation that script's own header says it exists to provide, and letting one workstream's
`rm -rf <workspace>` (SDD's closing step) delete another's ledger.

The pod's `docs/adr/0001-workstreams-use-the-pod-layout.md` blesses two fixes and names this one as
the fallback: **name the file `plans/<slug>/<slug>-PLAN.md`**, which this spine takes. The ADR's
nominal first choice — instruct SDD to use the slug — is declined because it is provably inert
against a script that ignores instructions. **What proves it held:** after B6's first task,
`ls .superpowers/sdd/` names `<slug>-PLAN/` and no `PLAN/` (acceptance criterion 13). **Fallback, with
its trigger:** if a future SDD version accepts an explicit workspace name, revert to `PLAN.md` plus
that instruction; the trigger is `sdd-workspace` gaining a name parameter. The docs stage amends ADR
0001 and `CONTEXT.md` to record that the fallback is now the rule.

## What a plan step carries

`writing-plans` requires real, runnable code in every step. That is right for a code deliverable
and wrong for a prose one. **A plan step carries whatever a fresh subagent with no memory needs in
order to produce the thing and prove it produced the thing — for code that is the code; for prose
it is the acceptance check.**

A prose step carries: the file and the section it writes; what that section must establish, in
requirements rather than sentences; the constraints and exact values it must use verbatim; and a
**runnable acceptance check** with what it returns when the work is correct and what it returns
when the work is absent. It does **not** carry a transcript of the prose to be written. Two
reasons, both structural: the plan is re-read on every task for the whole run, so a transcript is
paid for on every task and not once; and a step that contains its own answer cannot be reviewed —
the reviewer reads the answer instead of the requirement.

Measured: one release produced 4,161 lines of plan for a ~1,500-line prose deliverable, and that
plan is most of why its execution controller's context reached 829k.

**The one thing a prose step always copies verbatim is a template or an exact string the
deliverable must contain byte-for-byte.** Paraphrasing those is a separate, worse defect.

### The plan's task table, and its predicted spend

Every plan carries one task table, in this header order exactly:

```
| # | Task | batch | route | comparable | Acceptance |
|---|---|---|---|---|---|
| T1 | <what it builds> | b1 \| solo | claude:opus \| codex:gpt-5.6-sol:high | r2-B5 \| none | § <n> |
```

- **`batch`** — `b<n>` for a task dispatched in a fan-out block with its batch-mates, `solo` for one
  that commits its own paths. A batched task commits nothing: it returns its changed paths and the
  orchestrator commits each return separately, in batch order.
- **`route`** — `<seat>:<model>[:<effort>]`. The seat is a peer, not a junior: serious
  implementation is as eligible for the OpenAI seat as opinion-asking is, and the route is chosen
  per task by **fit**, bent by the week's consumption band rather than by a difficulty ceiling on
  either seat.
- **`comparable`** — `<corpus>-<row key>`, resolved through the plan's own key table, or `none` when
  nothing measured matches. An id the key table does not carry, or whose row key names no row in the
  named corpus, is a hard error and never a guess.

and one predicted-spend section, in this shape:

```
## Predicted spend

| task | comparable | billed est. | $ est. | min est. |
|---|---|---|---|---|

Total: $<n>, <n> min, over <n> dispatches. Rate: $0.635 per million billed tokens
(release 2: $173.94 / 273,955,454), 31 min per dispatch (13h / 25 boundaries).
Matched <n> of <n> tasks to a measured row.
```

Each task's return then carries one criteria row per criterion under its own acceptance heading:

```
CRITERIA: <n> of <n>
- [<criterion-id>] <the exact command that ran> → <what it printed, one line> [PASS|FAIL]
```

`<criterion-id>` is the identifier **verbatim** as the plan writes it — `AC9-size` and `A11` are
identifiers exactly as `AC3` is — and the trailing `[PASS]`/`[FAIL]` token is what lets a return
gate reject a *failing* row, which free-text output cannot carry. Beside each row goes the reason
the criterion was chosen, so a reader can tell a check that could have failed from one that could
not.

## The between-stages loop

After every stage return, the orchestrator does exactly this, in order:

1. **Read the return** — [the stage return](INTERFACES.md#the-stage-return). Nothing else from the
   subagent enters context.
2. **Verify existence and content against disk**, by the stage's output kind — everything marked
   "before" in [Output kinds](INTERFACES.md#output-kinds). Disk wins over the return, always. A
   root-level document in a CortexOS pod is invisible to git until `.gitignore` has its own `!` line
   — add the line, do not assume the file is untrackable. **Trackedness is not checked here.** A
   freshly written `file`-kind artifact is never yet committed at this point, so checking
   `git ls-files` now would fail every stage that just succeeded, read it as `blocked`, and hand it to
   step 3's cleanup below — which would delete the very artifact the stage correctly wrote.
   Trackedness moves to step 6, after the orchestrator's own commit has run.
3. **Branch on the verdict, after this verification:**
   - **`done`, and disk agrees** → step 4.
   - **`done`, and disk disagrees** → treat it as `blocked`, with the finding *"`done` claimed; disk
     says `<what verification found>`"*. This is the commonest way a stage lies without meaning to.
   - **`blocked`** → *clean up first*: delete any untracked file the stage left, and
     `git checkout -- <path>` any tracked file it modified. A half-written artifact left on disk is
     what makes the next stage read the wrong input. Then write the ledger block naming the blocker,
     and **re-dispatch the same stage once**, with the blocker named under
     [the dispatch brief](INTERFACES.md#the-dispatch-brief)'s *Honour these* and anything the
     orchestrator can resolve already resolved. **One re-dispatch per stage.** A second `blocked` on
     the same stage is a `stop`.
   - **`stop`** → write the ledger block, set frontmatter `verdict: stop`, commit, and report to the
     operator naming the stop condition and the exact command that resumes the run. **No next
     dispatch.** The session ends here.
4. **Write the ledger block**, using the canonical template at [STATE.md](INTERFACES.md#statemd);
   replace the frontmatter and *Resume here*. Every field there is `REQUIRED` — `**Commits:**` takes
   `—` for a kind with no commits of its own, never an omitted line.

   A review stage's block (B3, B5) is headed `### Stage <N> — <stage name>, <step> · <verdict> ·
   <date>` instead, where `<step>` is one of the four step names of
   [the review cycle](REVIEW_ROUNDS.md#the-cycle-and-what-closes-it) — `testing round`,
   `advisor read`, `rewrite`, `closure check`. **Never a round number.** The cap is gone and so is
   the numbering, so a block headed `round <n> of 3` is a run that did not follow that section, and
   the step names are what make the cycle countable from the ledger alone by anyone reading it
   afterwards. [Resume](#resume) reads the last step name to know where a review picks back up.
5. **Commit named paths only**, per
   [the orchestrator's commit, by output kind](#the-orchestrators-commit-by-output-kind) below. Never
   `git add -A`: `~/dotfiles` carries another surface's uncommitted work on `main`, and a bulk add
   bundles it.
6. **Confirm trackedness now that the commit has run**: `git ls-files` shows every path just staged.
   This is the trackedness half of [Output kinds](INTERFACES.md#output-kinds)'s verify column — run
   here, after the commit, and never before it.
7. **Dispatch the next stage.**

   **Dispatch blocking, and fan out in one block.** Every stage and task dispatch passes
   `run_in_background: false`, so the call returns the child's result inside the same turn. When
   several children are independent, issue **all** of their dispatches as multiple tool calls in a
   **single** message: they run concurrently and all return within that turn. **Never dispatch in the
   background and then end the turn** — a turn that ends while children are live is the stall, and
   every resume re-primes the whole context to learn something the blocking form would have handed
   back for nothing. Measured: two children dispatched this way returned in one turn, concurrently.

   **A fanned-out task owns a unique path and never a fixed one.** The scratch directory is shared by
   every subagent of a session, so two children that write `$SCRATCH/<fixed name>` collide — one
   overwrites, deletes or `git worktree add`-fails on the other's tree, and the loser reports a clean
   result from a fixture that is no longer there. Every dispatch that tells a child to write scratch
   state names a path unique to that child (`$SCRATCH/<task>-$$`, or any unique token), and the child
   removes only that path. Measured: one session's scratch directory held two different stage
   subagents' files side by side.

   Where the platform forces a background dispatch — a child that genuinely outlives a turn — do not
   improvise a wait: `subagent-driven-development/SKILL.md` § *Waiting on dispatched subagents*
   already specifies it (never poll with short timeouts, never sit in one silent open-ended wait,
   keep doing local work, reconcile live children between bounded stretches). Follow it there.

## The orchestrator's commit, by output kind

Step 5 above is not one instruction — four of the six output kinds have no single `<artifact>` path.

| Output kind | What the orchestrator stages and commits |
|---|---|
| `file` | `git add <ARTIFACT path> plans/<slug>/STATE.md` |
| `findings` | `git add plans/<slug>/STATE.md` — `ARTIFACT: none`, so nothing else changed on disk |
| `commits` | `git add plans/<slug>/STATE.md` — the subagent already committed each task by named path; this is a ledger-only commit |
| `files` | `git add plans/<slug>/DOCS.md <each ALSO CHANGED path> plans/<slug>/STATE.md` |
| `merge` | `git add plans/<slug>/STATE.md` — the merge commit is the subagent's; this is a ledger-only commit on top of it |
| `move` | `git add plans/<slug>/STATE.md`, committed **before** the move, at its pre-move path; the `git mv` and the `plans/INDEX.md` update are the orchestrator's own separate, later commit, staging the post-move path `plans/archive/<slug>` and `plans/INDEX.md` — see [Land, and the archive](#land-and-the-archive) |

`move` is the only kind whose ledger commit and its stage's own follow-up commit target different
paths, which is exactly the ordering [Land, and the archive](#land-and-the-archive) states once.

🛑 **`git add -A` and `git add .` are forbidden here, without exception** — the table above is
exhaustive; no seventh case needs a bulk add. `~/dotfiles` carries another surface's uncommitted work
on `main`; a bulk add bundles it into this workstream's commit, and that is a defect, not an
accident, however clean the tree looks at the moment of committing.

| Excuse | Reality |
|---|---|
| "`git add -A` is faster and the tree is clean anyway" | `~/dotfiles` carries another surface's uncommitted work; a bulk add bundles it, and that is a defect, not an accident. Measured (RED baseline, V16): an untracked `scratch-do-not-commit.txt` stayed dirty through a full two-stage run, and the subagent's own `git add` named exactly one path — `git add plans/fixture-workstream/PLAN.md`. The discipline held at RED because the always-on `atomic-commits` skill already forbids `-A`; this loop restates the rule locally so it does not depend on that skill staying loaded. |

## Resume

What a fresh build session with no memory does, in this order:

1. Read `plans/INDEX.md`; its in-flight row names the active workstream, which is `<slug>`.
2. Read `plans/<slug>/STATE.md`. **Absent** → no build session has run; read `BRIEF.md`, start at B1.
3. Read the frontmatter. `stage` and `verdict` are the *claimed* position.
4. **Verify the claim against disk; never trust it.** "The last completed stage" means **disk-done,
   not table-done**: for every stage the table marks `done`, run that stage's disk test from
   [Output kinds](INTERFACES.md#output-kinds) — a `file` stage's predicate is disk, checked with
   `git ls-files`: the file must be present **and** tracked; a `commits` stage needs its SHA range to
   resolve on the branch; a `findings` stage needs its ledger block present. The first stage whose
   test fails is the stage to run, whatever the table says — status is derived, never declared.
5. Read `BRIEF.md`. It is the controlling document for every remaining stage.
6. Read the last completed stage's artifact, because it is the next stage's input. Nothing else.
7. Run the stage named in *Resume here*, after reconciling it with step 4 — where the two disagree,
   step 4 wins.

It does not read the transcript, does not re-run a completed stage for context, and does not consult
the SDD ledger to decide its position. **The plan's own checkboxes are a competing signal and are not
consulted either**: they are written by implementer subagents and go stale the moment a task is
committed but its box is not ticked. `git log` against the task list is the tie-breaker.

**Three edge cases, all named because all will happen.**

- **A leftover artifact from a failed stage.** The between-stages loop deletes it, but a session that
  died mid-loop did not. So step 4 does not stop at "the file exists": an artifact present but
  **untracked** counts as absent, and the resuming session deletes it before re-running the stage.
- **Interrupted mid-Implement.** SDD's position lives in `.superpowers/sdd/<slug>-PLAN/progress.md`,
  which is git-ignored scratch and may be gone. Recovery is `git log` on the workstream branch against
  the plan's task list: the first task with no commit is the resume point, and the last ledger block's
  `**Commits:**` range bounds the diff to read.
- **Interrupted mid-review-round.** The review stage's ledger block records the round number and the
  open findings; the fresh session resumes at round N+1 carrying them. It does not restart at round 1,
  which would burn the cap.

**What brief assumption 3 probes.** Kill the skeleton run after one commit and restart it, checking
three things: the fresh session reads `STATE.md` before anything else; it re-runs no completed stage;
and with the frontmatter `stage` deliberately set one stage ahead of what is on disk, it resumes at
the stage disk says, not the stage the frontmatter claims.

## Land, and the archive

**B8 Land.** Three gates, in order:

1. **Full verification on the branch**, before the merge: the regression subset of the scenarios,
   plus `docs-graph-check.py`, scoped exactly as acceptance criterion 5 already scopes it: the script
   itself runs unscoped over the whole pod, but the gate is the intersection of its findings' paths
   with `git diff --name-only <base>...HEAD` — an empty intersection passes.

   Measure **twice, in two clean worktrees**, never against the live working tree:

   ```
   W="$SCRATCH/c13-$$"; mkdir -p "$W"          # unique per invocation — never a fixed name
   git worktree add --detach "$W/base" <base>
   git worktree add --detach "$W/tip"  HEAD
   python3 <dotfiles>/skills/plan/scripts/docs-graph-check.py --root "$W/base" | grep -vc '^exempt:'
   python3 <dotfiles>/skills/plan/scripts/docs-graph-check.py --root "$W/tip"  | grep -vc '^exempt:'
   git worktree remove --force "$W/base"; git worktree remove --force "$W/tip"
   git worktree prune; rm -rf "$W"             # removes only this invocation's own directory
   ```

   🛑 **The worktree paths are unique per invocation and never `$SCRATCH/base` / `$SCRATCH/tip`.**
   `$SCRATCH` is **one directory shared by every subagent of a session** — re-verified at round 2,
   which found round 1's `codex-prompt-b3r1.txt` sitting beside round 2's own probe files, two
   different stage subagents in one directory. Fixed names plus [§ 7.2a](#72a--the-blocking-dispatch-rule--ships-in-build_sessionmd)'s
   instruction to fan independent tasks out in one message is the brief's founding incident re-armed:
   `git worktree add` on an existing path fails, and a sibling's teardown removes your tree mid-walk.
   `$$` is the shell's own pid, which differs per invocation; any unique token does. Nothing is broken
   today only because the spine is sequential, and a defect that is latent because nothing has
   exercised it yet is not a defect that has been survived (ruling R87).

   `git worktree remove` takes **one** worktree per invocation (`-f <worktree>`), so the teardown is
   two commands. Round 2 measured what the two-operand form actually does: it exits **129 and removes
   nothing** — wrong in the safe direction, where this spec previously said it *"removes the first and
   errors on the second"*. The split form exits 0/0 and prunes clean.

   **The gate is the intersection, and only the intersection:** the tip's finding list ∩
   `git diff --name-only <base>...HEAD` must be **empty**. B8's Land step already defines exactly this
   gate; `C13` adds no second one.
   **Reported, never gated:** the two whole-pod counts, their delta, and the `diff` of the two finding
   lists naming every added and every removed line. They go into `DOCS.md`. A rise in the whole-pod
   total with an empty intersection is a **reported** fact, not a failure — `ADR 0005`, and ruling R6's
   accepted trade, which is that inherited debt this run did not introduce reaches the base branch
   unblocked and visible.
   **The positive control:** the base count must be **non-zero**. A `0` means the walk never ran —
   a wrong `--root`, an empty worktree — not that the pod is clean. Report it beside the result.
   **What it returns when the thing IS there:** the intersection's member lines, named. An empty
   intersection is a pass **only if** the base control passed and the tip walk produced a non-zero
   finding list; two zeros from a walk that never ran are indistinguishable from a clean run.

   Verified three times, most recently at the second revision: `git worktree add` works **inside the
   command sandbox with no `dangerouslyDisableSandbox` override**, changes no branch, and touches no
   tracked file; the whole add-measure-remove-prune cycle exits 0. **The plan budgets no override for
   it** — every probe of this mechanism has run sandboxed. This satisfies the constraint that neither
   repository's branch may change and that `git stash` is forbidden.

   `DOCS_STAGE.md`'s 175-finding baseline is pre-existing pod debt this workstream is not on the hook
   to fix, and a gate that re-litigates the whole tree on every workstream can never pass — not for
   this one, not for any future one (ruling R11: a gate whose pass condition is unreachable is worse
   than no gate — the first session to meet it learns to override the stage, and every session after
   inherits the habit — the general form is [CHECKS.md](CHECKS.md)'s rule 2).
   The unscoped total, and its delta against the baseline, is **reported** in `DOCS.md`, never gated
   on. This order is correct and deliberate — `finishing-a-development-branch` verifies in its own
   Step 1, before the merge menu in its Step 4.
2. **Merge** the workstream branch into the branch `STATE.md`'s `base:` names, inside the pod.
3. **Re-run `docs-graph-check.py` on the merged result, scoped the same way**: intersect its findings
   with `git diff --name-only <base>...<merge commit>`. A merge can break a link that both parents
   satisfied, and nothing else in the pipeline would see it; the scoping is identical to gate 1's, for
   the identical reason (ruling R11 again).

A failed verification, a merge conflict, **or** a post-merge check failure **on this workstream's own
diff** is a stop condition — the session halts and reports; it does not resolve a conflict on its own
judgement. A finding outside that diff is recorded in `DOCS.md`, never a stop condition.

| Excuse | Reality |
|---|---|
| "the conflict is trivial, I can resolve it" | A merge conflict is a stop condition; the session halts and reports and does not resolve on its own judgement. Measured (RED baseline, V9a): the subagent dry-ran the merge (`git merge --no-commit --no-ff`) and found a real conflict — "There's no objectively correct resolution — picking either side silently discards someone else's edit" — and aborted rather than resolving it, under the same offline-operator, sunk-cost pressure this gate must resist. |

**B9 Report and archive.** The report names verification evidence, the documentation checklist, the
pod's docs baseline and delta, and every decision taken without the operator, including where Codex
disagreed and was overruled.

**Ordering, stated once, because the two obvious readings contradict each other.** The orchestrator
writes and commits `STATE.md`'s final ledger block for B9 at its pre-move path
(`plans/<slug>/STATE.md`), exactly as [the between-stages loop](#the-between-stages-loop) does for
every other stage — the file cannot be moved before that commit exists, because the commit would then
name a path nothing occupies. **Only after that commit lands** does the orchestrator itself — not the
B9 subagent — run `git mv plans/<slug> plans/archive/<slug>` and move the `plans/INDEX.md` row, as one
further commit staging the post-move path `plans/archive/<slug>` and `plans/INDEX.md`. The B9
subagent's `MOVED:` line therefore names the *intended* target, never a completed move: the
orchestrator performs it and verifies it, not the subagent. Position is status.

⚠️ The spine does **not** invoke `plan-archive`: that skill's subject is `~/.claude/plans/*.md` —
Claude Code's own plan-mode files — matched to merged GitHub PRs by file overlap: a different set of
files entirely, and this pod is local-only with no remote, so its `archive-pr` and `backfill` modes
have nothing to match against. The pod-native retire is the `git mv` above.

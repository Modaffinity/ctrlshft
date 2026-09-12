---
surface: claude-code
date: 2026-08-12
status: reference — the ratified procedure, extracted from revision-scarred source
authority: outputs/IDEATION_DOSSIER-planning-execution-overhaul.md §13.1b (the procedure), §13.1c (its ratified output), and §8 fork 1 for the cost ladder — anchored on the phrase "The cost ladder, since \"borrow\" hides a five-way choice" (line 745 at rev 15, which is in progress; search the phrase, not the number)
runs: working/task1-funnel-rerun.md (second run, gate zero answered)
closes: vision/scope-items/v1-item-2.md — "the funnel", rung `ours`
---

> **This is a copy, not the canonical source.** The original lives at `docs/vision/FUNNEL.md` in
> the `ideas-skill` pod, where `docs/**` is gitignored — so that copy is never itself committed
> anywhere, and this dotfiles copy is the only version-controlled record of this content. It is
> mirrored here so the `plan` skill's pointers resolve for every project, not only from inside
> that pod's checkout. If the pod's working copy is revised, this file does not update itself —
> re-sync it by hand.

# The selection funnel

**How a version's scope is chosen from a vision deliberately larger than any one version.**

This is v1 item 2, whose gate-zero rung is `ours` — a process, not software. Nothing here is
built or installed; it is run by a person, with an assistant, at a version boundary.

The funnel exists because the expansive phase is **not the error and must not be suppressed**.
Putting every idea out, researching what ideal looks like and building the full vision is how the
operator comes to understand the problem. What was missing is the step *after* it: *"we have all of
this; now what do we actually build for version one?"*

**The vision is a corpus to select from, not over-scoped work to cut back — this phase is selection,
not subtraction.** That distinction is the whole mechanism. Cutting a plan feels like loss and gets
resisted; choosing v1 from a rich corpus feels like focus, and the remainder is inventory rather
than waste.

**Who decides.** Scoping is **operator-led and advised** — the operator's call, informed by the
session assistant *and* a cross-model review, at every version boundary. The operator decides; he
does not intend to decide unassisted. Nothing in this document ratifies anything.

**When it runs.** At every version boundary, not once. After a version ships, what it taught
reshapes the vision and the next version is scoped the same three-way. It runs alongside the
[boundary ritual](BOUNDARY_RITUAL.md), which is the other half of the same sitting.

---

## Reading note — what is ratified, what is superseded, what is open

The source section (§13.1b) interleaves the ratified procedure with the superseded reasoning that
produced v1's scope, on purpose: strikethroughs, reversals and revision notes were left in place so
the history stays auditable. **That is exactly what makes it unusable as a reference**, so this
document separates them. The separation below is the claim; the procedure that follows carries only
the first row.

| Material in §13.1b | Status | Carried here? |
|---|---|---|
| Selection-not-subtraction · three outcomes · the four questions · the value floor · deferral-with-recall | **Ratified**, on the **in-line operator attributions** — *(operator, round 10)* on the funnel and the value floor, *(operator, block 10)* on the three outcomes. All of it is *procedure* | **Yes — this is the document** |
| Gate zero | **Ratified separately and later** — *(operator, round-2)*, i.e. **R57**, *after* round 10. Until it existed the funnel silently assumed that surviving the four questions meant "build" | **Yes** — Step 2 |
| The cost ladder (§8, fork 1 — *"The cost ladder, since 'borrow' hides a five-way choice"*) | **Ratified** *(operator, round 10)*, with **buy** added in **round-2**, having been missing entirely. §M holds only the *posture* — "most of the time, do not build at all" — while the ladder itself sits under §8's fork 1; the dossier separates the two where it introduces gate zero | **Yes** — quoted verbatim below |
| "First candidates the operator named" | Labelled in-source as *"examples, not the v1 scope"* | No — never was scope |
| Everything after the ⚠️ marker: *"v1 is the vision layer, implemented"*, the four jobs, the "v1 additions" working list | **Superseded in scope** by the 2026-08-11 ratification. Retained in the dossier as *reasoning*, not as scope | No — it is v1's output, not the procedure |
| The plan stress-test's ✅ round-2 reinstatement into v1 | **Reversed, finally, 2026-08-11 (R63)** — deferred on **cost**, not on worth; the defence of its value stood entirely | Cited once, as the cost-misclassification lesson |
| Mermaid movement view | **Deferred at R63 (rev 12)** — the same ruling as the stress-test, and the cut the source calls its least certain | No |
| "The router: no — but the choice must be offered" | **Survived** into the ratified table as item 8 | No — scope, not procedure |
| The middle bucket's decision rule | **Open** — flagged unresolved at R57(d) after two live runs | Yes, as a **proposal only** — see the last section |

**The authoritative output of the two runs is the eight-item table at §13.1c.** Where §13.1b's
prose and that table disagree, the table wins — the dossier says so itself.

⚠️ **Do not read §13.1b's ✅ marker as ratifying this procedure.** It ratifies *"the shape below"* —
and the ⚠️ marker four lines later supersedes exactly that block (row 4 above). The two markers sit
close enough together to be mistaken for a general seal on the section; they are not. The procedure's
authority is the per-element operator attributions in rows 1–3, which is why they are cited
separately, and why **"round 10" is not the whole story: gate zero arrived at round-2, later.**

### Three things this extraction could not resolve

Stated rather than guessed, because a confidently-stated wrong rule is worse than a flagged
uncertainty.

1. **A stale section pointer in the source.** §13.1b's superseded marker directs the reader to
   *"the eight-item table at the end of §13.1b"*; that table is actually headed **§13.1c**. Nothing
   turns on it — both phrases denote the same table — but the identifier in the text is wrong, and a
   reader searching §13.1b for a table will not find one.
2. **The cost ladder and the record schema do not use the same words.** The ladder's rungs are
   *consume · buy · vendor · fork and modify · build*; `vision/schema/rules.py` permits
   `obtained_by` values `build · buy · borrow · consume · ours`. So **`borrow` is not a ladder rung,
   `vendor` and `fork and modify` are not schema values, and `ours` has no rung at all.** Observed
   usage suggests `borrow` spans the ladder's two middle rungs (item 4's borrow — changesets plus
   Keep a Changelog — is a convention taken unmodified, i.e. vendor-shaped) and that `ours` is what
   a *process* gets, which a ladder about software never had a place for. **No source ratifies that
   mapping**, so it is recorded here as observation. If it matters to a decision, ask.
3. **The middle bucket has never actually been used.** All eight ratified items carry Q1, Q2 or Q3;
   not one is recorded as low-hanging fruit. After two runs the category has **zero instances** —
   which is context for the proposal at the end, and is the strongest single argument that its
   decision rule is genuinely missing rather than merely unwritten.

---

## The procedure

### Step 0 — assemble the corpus and fix the frame

- [ ] The vision, entire, is the input. Do not pre-trim it — pre-trimming is subtraction, and
      subtraction is the failure mode this replaces.
- [ ] Name the version being scoped (a coordination point: `vision/coordination-points/`).
- [ ] State the three outcomes out loud before starting, so the middle one is not forgotten:
      **must-have · low-hanging fruit · deferred**. A binary must-have/deferred split is too coarse
      — the middle bucket is what stops a lean version from being needlessly bare.

### Step 1 — the four questions, applied to every item in the vision

Run all four per item. **An item is must-have if any of the first three is true; low-hanging fruit
if none are but its cost is near zero; deferred otherwise.**

- [ ] **Q1 — Can the version run at all without it?** If no → in.
      *The minimum-viable-probe rule: a bike without wheels teaches nothing about the road.*
- [ ] **Q2 — Does its absence stop the version teaching us the shape?** If yes → in.
      A lean version's real product is what it reveals (R25), so anything load-bearing for
      *learning* is essential even when it is not a feature. The **usage receipt** is the type case.
- [ ] **Q3 — Is it a control the safety floor or the autonomy envelope requires?** If yes → in,
      **unconditionally**. Process weight is selectable; controls never are (R24).
- [ ] **Q4 — Does its value depend on evidence only this version can produce?** If yes →
      **deferred by construction, not by preference.** Building it now would be guessing.

Q4 is the one that is not a judgement call. If an item's right shape is unknowable until the version
has run, deferring it is the only honest move, and saying so removes the argument.

### Step 2 — gate zero, applied to every item that survives

**Nobody skips this.** The four questions decide *whether* an item belongs in the version. They do
**not** decide that it must be **built** — and until this gate existed the funnel silently assumed
they did.

> **No item is classified as "build" until someone has actually looked** — on GitHub, in existing
> skills, or as something purchasable.

Three properties that make it real rather than aspirational:

- **"Buy" is a first-class option.** Paid tooling counts. It was missing from the ladder entirely
  until round-2. Someone else's maintenance is worth money when the operator's hours are the scarcer
  currency.
- **The search is research** — run it with the existing `research` skill. It is not a new mechanism,
  and it produces a filed scan (the second run's is `research/build-buy-borrow/`, README plus 01–08).
- **It applies to the version's own components.** Before building a roadmap, a change-management
  flow or a visualisation, look for what already does that — *"perhaps we get a ton of stuff for very
  little effort."*

**The cost ladder, since "borrow" hides a five-way choice:**

> **consume · buy · vendor · fork and modify · build**

| Rung | What it means | What it costs |
|---|---|---|
| **consume** | take the upstream package as-is; it maintains itself | the only genuinely free option — what Superpowers is today |
| **buy** | a product that already does the job | money, in exchange for someone else's maintenance |
| **vendor** | a whole component taken in, unmodified | cheap to take, yours to update |
| **fork and modify** | change what you took | the cost reviewers ask you to price |
| **build** | author it yourself | the most expensive, and the last resort |

- [ ] Walk the ladder **top-down** and stop at the first rung that works. Preference runs down it;
      **every step down must be justified.**
- [ ] Record **which rung**, and the evidence for it, on the scope item (`obtained_by`).
- [ ] Record what the chosen rung **does not** get you. A buy that covers four of six requirements
      is a buy plus two things that stay yours — write down which two, *"or a later session will
      assume otherwise."*
- [ ] Prefer **whole components** from well-used, actively maintained repositories — big Lego
      bricks, not fragments — and own only the glue. Each forked part must **name why borrowing
      failed**.

> ⚠️ **Whatever we copy stops being free at the moment we copy it.** And the cost that gets
> mis-read is *authoring*: the one measured error in two runs was the plan stress-test, classified
> **CONSUME** when *"settle what the register can settle, run the four de-risking moves, amend the
> plan"* is a **build**. It was deferred on that correction alone (R63), its value never in dispute.

### Step 3 — the value floor, once, on the selected set as a whole

The four questions bound the version from above. This bounds it from below.

> **A version lean enough to add no value is not lean, it is pointless.**

- [ ] State what the version must beat: **the do-nothing alternative, or the existing process it
      replaces.** For a skill specifically, that is *the model with no skill at all*, or the skill
      being replaced — the no-guidance control that authoring already makes mandatory, applied here
      as a **scoping floor** rather than only as a publishing gate.
- [ ] Where there is time, test it.
- [ ] Where there is not, **record the claim as belief** — *belief is a legitimate answer and an
      unmarked belief is not* — together with **what would confirm it**, so a later round knows
      which floors were measured and which were assumed.
- [ ] Check the confirming test is **falsifiable**. This is where the second run failed once and was
      corrected: *"the operator is still using it"* proves persistence, not value, and cannot
      distinguish usefulness from sunk-cost continuation. It was replaced (R68) with three concrete
      checks that now run in the [boundary ritual](BOUNDARY_RITUAL.md).

### Step 4 — record the outcome, in records rather than prose

Everything deferred is marked **not now, with its reason and the evidence that would recall it**, so
a later round *retrieves* it rather than rediscovering it.

- [ ] One `vision/scope-items/` record per selected item — `id`, `name`, `coordination_point`,
      `obtained_by`.
- [ ] One `vision/deferrals/` record per deferred item — `id`, `name`, `why_not_now`, `recall_when`,
      `observable`. `observable: false` is an honest answer and is used: it marks a recall condition
      with no trigger, which the deferral walk then judges by hand.
- [ ] One `vision/changes/` record per **movement** — write-once, sealed, with the `reason` as a
      first-class field. A log gives what/when/who free and never gives *why*.
- [ ] `python3 vision/schema/validate.py vision` → `0 failure(s)` before the sitting closes.

---

## Worked example — the version/roadmap layer, from the second run

The best example is one where **gate zero changed the answer**, because that is the step the funnel
was missing. Source: `working/task1-funnel-rerun.md`.

| Step | What happened |
|---|---|
| **Q1–Q4** | **Must-have on Q1** — nothing else in the version can run without somewhere to hold and display the version model. Verdict unchanged by everything that follows. |
| **Gate zero — the search** | Run as research: two scan rounds, nine-plus products, a cross-model challenge, and an alternatives pass that came back empty on the deciding axis. Filed at `research/build-buy-borrow/`. |
| **Gate zero — the ladder** | **consume** — fails: Plane's Community Edition is *"at par with the Free tier of the Cloud edition"* and ships neither Initiatives nor Releases, so free-and-self-hosted never delivered the version model. **buy** — clears: **Plane Business, ~$13/seat/mo, cloud, one seat.** Stop. `vendor`, `fork and modify` and `build` were never reached. |
| **What the buy does not buy** | Recorded explicitly, as its own table. **MA3, the append-only "what moved and why", is not bought and no product sells it** — so the change record **stays ours** and became item 4, recorded `obtained_by: borrow` — changesets as the write path, Keep a Changelog as the read view, both taken unmodified. **MA5, state on disk, is partial**: Compose covers work items, schemas, cycles, modules and milestones; not Releases, Initiatives or Pages. |
| **What is still unverified** | Two facts the ruling rests on, flagged rather than assumed: that **Releases are in Business and not Enterprise** (*"confirm at signup before paying"*), and whether **Milestones can serve as the version model** and round-trip through Compose. |
| **Value floor** | The version beats do-nothing (ideas in chat, one implementation at a time) — recorded as **belief, not measurement** (N12), alongside the separate belief that the bought surface will actually be **opened voluntarily** (N13/J6). |
| **The correction that followed** | The original confirming test — *"the operator still using it after the first version boundary"* — was called unfalsifiable by the third adversarial review and **replaced (R68)** by the three checks now in the boundary ritual. **The floor is the step most likely to produce a comfortable, untestable claim; write the confirming test as if someone will try to fail it.** |

**Two shorter passes, for contrast.** Item 6 (adversarial review plus the boundary ritual) stops at
the **top** rung — `consume`, the existing `ask-codex` lane, cost ~0, no search needed because the
thing already runs here. Item 2, this funnel, is `ours`: no rung fits, because there is no software
to obtain.

**The net, taken from the ratified table and nowhere else:** of eight items, **three are builds
(1, 5, 8) · two buys (3, 7) · one borrow (4) · one consume (6) · one `ours` (2)**. In the dossier's
own words, *"the entire build surface is items 1, 5 and 8"* — a schema, a capture step, and a prompt
that offers a choice. **That is the point of gate zero:** v1 came out *smaller* after a day that
added two findings, because gate zero converted presumed builds into a purchase.

> 🛑 **Do not quote the second run's own closing summary** (`working/task1-funnel-rerun.md`, "Net
> effect on v1": *"four are borrows, two are consume, two are small builds… nothing is worth
> buying… the €100/mo ceiling went unused"*). **It is stale inside its own file** — superseded by
> the operator ruling prepended above it in the same document (BUY, Plane Business, $13/mo) and then
> by §13.1c. Every count in it is wrong now, the ceiling was **not** unused, and its "two consume"
> includes the plan stress-test — **the exact CONSUME mis-classification this document teaches at
> Step 2.** It is the sharpest live example of why the reading note above exists: a superseded
> summary reads as authoritative precisely because it is a summary.

---

## The open rule — the middle bucket

> 🟡 **PROPOSED, NOT RATIFIED.** The operator ratifies scope decisions; this document does not. What
> follows is a proposal with its reasoning exposed so it can be rejected on the reasoning.

**The open question, stated exactly.** R57(d) left *"low-hanging fruit"* unresolved as a funnel
category, and it was still unresolved after the second run. The *bucket definition* exists — "none
of Q1–Q3 is true, but its cost is near zero" — and both runs recommended **keeping the category**.
What has never been settled is the **decision rule**: what counts as near-zero, and whether landing
in the middle bucket is by itself enough to ship.

**What the evidence says.** Three facts, all checkable:

- **The category has zero instances after two runs.** Every one of the ratified eight carries Q1, Q2
  or Q3. A category that never fires is either unnecessary or missing its rule.
- **It has a real class to catch — but every named example is an *adjacent* case, not an instance.**
  The source offers two: items 7 and 8 cost approximately zero and *"would lose against must-haves
  without a middle bucket"*; and the scan moved four items from presumed-build to rename-cost borrow,
  *"exactly the class the middle bucket exists to catch"*. ⚠️ **Neither could ever enter the bucket
  under condition 1**, because items 7 and 8 carry **Q2** and the four rename-cost borrows are all
  Q1 or Q2 items. What they demonstrate is the *cost profile* the bucket is meant to admit; they do
  not demonstrate the bucket. **The proposal below is therefore extrapolated from adjacent cases,
  with no instance to fit it to** — which is the honest weakness in it, and the source is loose in
  exactly the same way where it argues for keeping the category.
- **The bucket is also the obvious drift vector.** v1 had drifted to **14 items** before the funnel
  was re-run on itself — the very drift it was scheduled to stop. "It's cheap, throw it in" is how
  eight becomes fourteen, one defensible addition at a time.

### The proposed rule

**Cheap is necessary and never sufficient.** An item enters the middle bucket only when **all four**
hold:

1. **It fails Q1, Q2 and Q3.** If any is true it is a must-have and this bucket does not apply.
2. **Its ladder rung is `consume`, `buy` or `vendor` — never `fork and modify`, never `build`.**
   Stated in **ladder rungs, not schema values**, because the two vocabularies do not line up (see
   the reading note): a record saying `borrow` may be a cheap `vendor` *or* an expensive `fork and
   modify`, so the question to ask of any `borrow` is **which rung is it really?** The moment an item
   requires authoring — or modifying what it took — its cost is not near zero, whatever it looks like.
3. **It rides a named must-have already in the version** — a field on a schema being written anyway,
   a rename, one more path in a review that already runs. **Name the must-have.** If none can be
   named, the item is not low-hanging; it is merely small, and small is not a reason.
4. **The bucket is filled in one pass, after the must-haves are frozen**, from a list the operator
   sees in full. Nothing is added to it after selection closes.

**And it is audited afterwards:** at the next boundary, each middle-bucket item's actual cost is
compared with its claimed near-zero cost. Repeated overruns are grounds for the operator to tighten
the rule — the bucket earns its place or loses it on evidence rather than on argument.

### Why this shape, and why no number

- **Condition 2 is empirically motivated, not aesthetic.** The single measured cost error across two
  runs went in precisely this direction: the plan stress-test *looked* like CONSUME and was a build.
  Excluding the authoring rungs from the cheap bucket costs one true positive at worst and closes the
  one failure mode that has actually occurred. Stating it in rungs also keeps `vendor` — *cheap to
  take, yours to update* — **in**, which a rule written as "never `build`" over schema values would
  have silently dropped while letting `fork and modify` through.
- **Condition 3 is extrapolated from the adjacent cases, not read off instances.** There are no
  instances. What the four rename-cost borrows have in common is that each attached to something
  already committed, and that is what makes "near zero" checkable without measuring anything — but
  they were must-haves, so this is a generalisation from their *cost shape*, offered as the most
  defensible available and not as an observed regularity.
- **Condition 4 is the smallest structural stop for the drift**, and costs nothing: it changes when
  the bucket is filled, not what may go in it.
- **No numeric threshold is proposed, deliberately.** The same source declined to invent observable
  thresholds for the deferral conditions (R67) on the grounds that *"three new metrics would be
  applied confidently and wrongly, which is this document's own recorded over-modelling failure."* A
  percentage cap on the middle bucket would be the same mistake in a new place. **The audit replaces
  the number**: it uses real observed cost instead of a guessed one.

**What would falsify the proposal.** A version boundary where a genuinely worthwhile item fails only
condition 3 — cheap, not a build, but attached to nothing already in scope — and the operator wants
it anyway. If that happens more than once, condition 3 is too strict and should become a prompt
rather than a gate.

---

## What this document deliberately does not carry

- **v1's scope.** That is `vision/scope-items/` and dossier §13.1c. This is how scope is *chosen*.
- **The superseded reasoning.** It is not deleted — it lives in §13.1b, marked, and stays there for
  anyone reconstructing how the shape was arrived at. It is simply not procedure.
- **Any ratification.** Every proposal here is labelled as one.

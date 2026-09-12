---
surface: claude-code
date: 2026-08-12
status: reference — first implementation of the ritual; the adversarial half already runs
authority: outputs/IDEATION_DOSSIER-planning-execution-overhaul.md §13.1c row 6 and "The first version boundary — one ritual, three jobs" (rev 13, R67 + R68 + R70)
consumes: ~/dotfiles/skills/ask-codex (the fenced cross-model lane)
closes: vision/scope-items/v1-item-6.md — "adversarial review and the boundary ritual", rung `consume`
---

> **This is a copy, not the canonical source.** The original lives at
> `docs/vision/BOUNDARY_RITUAL.md` in the `ideas-skill` pod, where `docs/**` is gitignored — so
> that copy is never itself committed anywhere, and this dotfiles copy is the only
> version-controlled record of this content. It is mirrored here so the `plan` skill's pointers
> resolve for every project, not only from inside that pod's checkout. If the pod's working copy
> is revised, this file does not update itself — re-sync it by hand.

# The boundary ritual

**What happens at every version boundary, in one sitting, on top of a review that already runs.**

This is v1 item 6, whose gate-zero rung is `consume`: the thing being consumed is the **`ask-codex`
lane**, which exists, is fenced, and has already run eleven scoped reviews in this repository. The
ritual adds no software. It adds a **checklist to a review that happens anyway** — which is why its
recorded cost is zero.

It has two halves, and they are different in kind:

| Half | Status before this document | What it is |
|---|---|---|
| **Adversarial review** at the vision and at **every** version selection | **Already running** — eleven `evidence/codex-scoped-*/` runs; three adjudicated rounds against the dossier, **every one of which returned REJECT** | consume the `ask-codex` lane |
| **The ritual's jobs** — the deferral walk, reconciliation, the value-floor test | **Zero implementation of any kind.** No checklist, no script, no process artifact | this document |

**Why the ritual exists at all is itself a result of the first half.** The third adversarial review
found that *"v1 has version-boundary reviews but never requires them to evaluate deferred items, so
nothing is wired to recall anything"* — and that the value floor's confirming test was
unfalsifiable. Both findings were accepted and both fixes landed **here** (R67, R68). The deferral
walk is the wire.

Run it with [`FUNNEL.md`](FUNNEL.md) — the funnel selects the next version, this ritual closes the
one before it. Same sitting, same operator, same evidence on the table.

---

## Part 1 — the adversarial review (the consumed lane)

### Where it goes, and where it must not

**Put it where nothing else checks.** Code has tests, a compiler, and a fresh per-task reviewer;
**decisions have none of those**, and a wrong decision is the expensive kind to discover late.

| Point | Why here |
|---|---|
| **(a) The vision** | a wrong vision propagates into every plan beneath it |
| **(b) Every version selection — v1, then v2, then v3** | choosing the wrong thing to build is the costliest failure named in the source, and the funnel's output is otherwise **unchecked by anything**. This is the recurring gate, not a one-off |
| **(c) The plan, before implementation** | the last point before cost is committed |

🛑 **Not inside the implementation loop.** Superpowers already runs a fresh reviewer per task; a
second one there duplicates a working check, which is the over-testing failure. **The supporting
evidence is that both cross-model reviews caught *decision* errors — a missing mission criterion, a
scope ratified ahead of its own experiment — not execution errors.**

*Reading note: "both" is verbatim from the source, which was written when **two** rounds had run.
A third has since run and it strengthens the same point rather than weakening it — its findings 4
and 5 are the two decision errors that created this ritual. Read "both" as "every round so far".*

### The invocation

`scoped` is the mode: it copies the paths you name into an empty directory and Codex sees nothing
else. That is what fits here, because a boundary review reads **documents**, not a diff.

```bash
ask-codex scoped \
  outputs/IDEATION_DOSSIER-planning-execution-overhaul.md \
  vision/ \
  docs/vision/ \
  research/build-buy-borrow/ \
  -- 'You are an independent adversarial reviewer of a version selection. Do not review the
      documents generally — attack the selection itself, hard, and prefer one decisive objection
      over a list of plausible ones. If a claim survives, say so plainly: a confirmation is a
      useful result. (1) Did we cut the wrong things? Name the single most wrongly deferred item
      in vision/deferrals/ and say why. (2) Is any recall condition wishful — a trigger with no
      observer and no threshold? (3) Does the selected set clear its value floor against
      do-nothing, or is the floor asserted rather than tested? (4) What is in scope that the four
      questions do not actually justify? Cite file and line for every claim.'
```

**Four things about this command that are not optional:**

- ⚡ **Bypass the calling harness's command sandbox on the *first* call** — under Claude Code that
  is `dangerouslyDisableSandbox: true`. This is not a workaround applied after a failure: the fence
  is the wrapper's own policy files (`~/.codex-agent/*.config.toml`) plus an empty working
  directory, and the harness sandbox contributes nothing to it. Sandboxed, the run fails with exit
  5 and *"failed to initialize in-process app-server client: Operation not permitted"* **after
  copying every byte of the fence in** — the wasted call is not free on a large scope.
- ✅ **`scoped` copies from disk, so it reads gitignored files perfectly well.** This matters more
  here than anywhere: `vision/`'s instance records, `docs/` and `research/` are Dropbox-carried and
  mostly outside git. The review can see all of them. What it cannot do is cite a commit sha for
  them — **evidence that lives outside git is pinned by content hash, not by commit**.
- 🛑 **A blocked, missing or failing `ask-codex` is a stopping condition, not a routing decision.**
  Do not substitute `mcp__codex__codex`: it takes a `config` object that reaches `sandbox_mode`
  directly, no permission rule can bind an object, and the substitution converts a fence into a
  silent loss of containment that nobody downstream can detect. Report what it needs — an approval,
  a `bootstrap.sh` run, a `codex login` — and stop.
- ⚠️ **Not `review` mode.** `review` reads the whole working tree, *including previous review
  reports lying in `evidence/`*, and has been observed reporting a defect it read in an earlier
  report as though it had found it. At a boundary you are counting findings and asking whether an
  objection is **novel**; `review` cannot tell you that.

### Reading what comes back

- [ ] **Judge the artifact, never the exit code.** Codex returns exit 0 on a refused write. The
      *wrapper's* exit code is a real verdict (`0` completed · `1` gate FAIL · `2` suite never ran ·
      `5` the run left nothing trustworthy); Codex's own is never passed through.
- [ ] **Check the report's frontmatter against its findings.** It states the run's reach. **A
      finding naming a file outside that reach is a guess**, and should be taken literally as one.
- [ ] **Verify every finding against the files before adjudicating it.** That is how the three
      previous rounds were handled and it is the reason their adjudications hold.
- [ ] **Adjudicate every finding explicitly — accepted, accepted-in-part, or declined with a
      reason.** No silent discards. Declining is legitimate: R67's third proposed fix was declined
      because inventing three observable thresholds would have been the over-modelling failure the
      source has already recorded twice.
- [ ] The run files itself at `evidence/codex-scoped-<stamp>/` — nine files: `REPORT.md`,
      `invocation.txt`, `prompt.txt`, `scoped-paths.txt`, `scoped-manifest.txt`, `commands-run.txt`,
      `policy.txt`, `stream.jsonl`, `codex-stderr.log`. That directory **is** the evidence; nothing
      needs copying out of it. `scoped-manifest.txt` is what tells you the fence actually held —
      it lists what was copied in, against `scoped-paths.txt`'s list of what you asked for.

**Known refusal with a one-line fix:** exit 4 naming `branch.*.vscode-merge-base` — VS Code writes
that git config key routinely. `git config --unset-all branch.<name>.vscode-merge-base`, then retry.

---

## Part 2 — the three jobs

Everything the version needs to learn about itself happens at the same moment, so all three run in
the same sitting as the review above.

⚠️ **Three, not two — the source states the number two ways.** §13.1c's row 6 names the ritual as
*"the deferral walk and the value-floor test (R67 + R68)"*, while the ritual's own specification —
*"The first version boundary: one ritual, three jobs (rev 13, R67 + R68 + R70)"* — adds
**reconciliation**. The row credits R67 + R68 only, and R70 is the later ruling of the same
revision — so the row reads as a summary that was not amended when the third job arrived. **The
specification governs**: it is the ratified detail, and its rule that the ritual **cannot be marked
complete with an unexplained mismatch** is load-bearing. This document follows it, so it lists three.

### Job 1 — the deferral walk (R67)

**Enumerate every record in `vision/deferrals/` and record `met` / `not met` / `cannot assess` with
evidence.** Not a sample, not the interesting ones — all of them. The walk is what makes a weak
recall condition survivable: it guarantees a human judges it on a schedule.

- [ ] `ls vision/deferrals/*.md | wc -l` — confirm the count against the table below before you
      start. **A stable count can hide a changed list**: at rev 13 one deferral left the table and
      another joined it, seven out and seven in, and that swap was stated precisely because the
      number did not move.
- [ ] For each record, read `recall_when` and test it against **current reality**, not against
      intent.
- [ ] Record the verdict with its evidence. **`cannot assess` is a legitimate verdict** and is the
      honest one for the three records whose `observable` is `false`. *"`cannot assess` is a
      legitimate answer; nobody looking is not."*
- [ ] **One entry per deferral per boundary — all seven, every time, not only the ones that move.**
      The source rules on the store and needs no new one: *"one entry per deferral per boundary is
      item 4's append-only record, with the reason as a field (F5)."* ⚠️ **The schema as built cannot
      hold that yet** — see [Closing the sitting](#closing-the-sitting) before you try.
- [ ] Any deferral that comes back → it becomes a scope item on the next version, **and the movement
      gets a `vision/changes/` record** with the reason as a field. This one *does* validate today:
      it is a `scope_membership` movement, which is the dimension deferrals are permitted.
- [ ] Honour `on_recall` where present. One record carries it today: the plan stress-test says **run
      gate zero first**, because testing and verification frameworks are a crowded field and this is
      *"exactly the item likeliest to be built by default without anyone having looked."*

**The seven deferrals, as they stand at the time of writing** (`observable: false` marks a condition
with no trigger — those are the ones the walk exists to judge):

| # | Record | `recall_when` | `observable` |
|---|---|---|---|
| 1 | `df-write-down-automation` — write-down automation (funnel → Plane) | Retyping decisions becomes a named friction, or a second project starts | `true` |
| 2 | `df-knowledge-work-verification` — knowledge-work verification contract | The first deck or report goes through Cowork and we can see what actually goes wrong | `true` |
| 3 | `df-vision-building-process` — vision-building as a codified process (job 1) | A second person must run it, or the conversation stops producing usable visions | `true` |
| 4 | `df-file-plane-reconciliation` — automated file↔Plane reconciliation | The manual check finds a drift it **cannot explain**, or a second project starts | `true` |
| 5 | `df-generated-many-branch-docs` — generated many-branch documents | ⚠️ none — *"enough branches"* and *"stop being readable"* are both undefined. **Judged at this walk** | `false` |
| 6 | `df-mermaid-movement-view` — Mermaid version-movement view | ⚠️ none — *"becomes painful"* is unfalsifiable. Nearest real event is the Plane pilot's movement-history check | `false` |
| 7 | `df-plan-stress-test` — plan stress-test | ⚠️ none — *"stable"* and *"the observed bottleneck"* have neither threshold nor observer. **Depends entirely on this walk** (`on_recall`: run gate zero first) | `false` |

**Four of the seven can fire on a recognisable event; three cannot.** That asymmetry is recorded
rather than fixed — no thresholds were invented for the three, deliberately. **They are the reason
the walk is a scheduled human judgement instead of a query**, and the person walking them should
expect to spend most of the job on rows 5–7.

**Row 6 is the least certain cut in the set.** If Plane's own views turn out not to show *movement
with its reason*, the change record is readable only as files — against a stated requirement that
the operator **enjoys** working in it. Check it against the Plane pilot's evidence rather than
deciding by feel.

### Job 2 — reconciliation (R70)

- [ ] Compare the model files (`vision/`) against Plane, and **record the result**.
- [ ] `python3 vision/schema/validate.py vision` → expect `0 failure(s)`. This checks the files
      against themselves — required fields, enums, id uniqueness, references, ownership, and the
      write-once seals on `vision/changes/`. It does **not** check Plane; that half is manual in v1
      and the automated diff is deferral #4 above.
- [ ] 🛑 **The ritual cannot be marked complete with an unexplained mismatch.** Explaining a
      mismatch is a legitimate close; leaving one open is not. That rule is the whole reason drift
      here is *bounded* rather than merely admitted.

### Job 3 — the value-floor test (R68)

Three checks, replacing *"is the operator still using it"* — which the third review correctly called
unfalsifiable, since continued use *"proves persistence, not value… cannot distinguish useful vision
management from sunk-cost continuation or simply liking Plane."*

**Each check tests a different item**, so the floor decomposes into per-item evidence instead of one
global impression.

| # | Check | What it tests | Binds |
|---|---|---|---|
| 1 | Can the operator **reconstruct what moved and why**, from the record, **unaided**? | item 4 — the append-only change record | N12 |
| 2 | Did he **actually use retained receipts** to choose the next version, rather than recall? | item 5 — receipt capture | N12 |
| 3 | Does he **voluntarily return** to it? | item 3 / J6 — the bought surface | N13 |

- [ ] Run check 1 as an actual reconstruction, not as a question about whether it would be possible.
- [ ] Run check 2 against the funnel sitting that is happening in the same session — *were receipts
      on the table when the next version was scoped?* If the answer is "we remembered", it is a fail.
- [ ] Check 3 speaks to **enjoyment** rather than utility, and it is the axis this estate most often
      gets wrong: **non-use is its most-recorded failure.**
- [ ] **On failure, record the result and let it inform the next version's scoping. It triggers
      nothing automatically** — instruments *inform* operator judgement rather than determine it.
      Wiring a failed floor to a stop signal was considered and **declined**: the honest version of
      that question is comparative (*is the next increment here worth less than the same effort
      elsewhere?*), and that comparison is explicitly deferred.

> **Note what this buys: there is now an outcome in which we would conclude the version did not
> clear its floor.** That is the point of having replaced the old test, and the ritual is worthless
> if the three checks are run as formalities.

---

## Closing the sitting

- [ ] The `evidence/codex-scoped-<stamp>/` directory exists and its findings are adjudicated.
- [ ] All seven deferrals carry a verdict with evidence.
- [ ] Reconciliation recorded; **no unexplained mismatch**; `validate.py` clean.
- [ ] Three value-floor checks answered, including any fail.
- [ ] Every movement the sitting produced — a recalled deferral, an item moved between versions — has
      a write-once `vision/changes/` record carrying its `reason`.

### Where the sitting's own result is written — and the one gap between the ruling and the model

**The store is ruled, not open.** The source is explicit that the walk needs no new one:

> *"It needs no new store: one entry per deferral per boundary **is** item 4's append-only record,
> with the reason as a field (F5)."*

So the intended shape is **seven entries per boundary in `vision/changes/`**, one per deferral,
verdict and reason carried as fields — not one entry for the few that moved.

🚩 **The schema as built cannot hold that today, and this is a real finding rather than a
preference.** `vision/schema/rules.py` permits a **deferral** to be the subject of exactly one change
dimension — `scope_membership` — whose endpoint must resolve to a scope-item or coordination-point
id, or to the reserved `deferred` / `none`. A per-boundary **verdict** (`met` / `not met` /
`cannot assess`) is not a movement along that dimension and has no valid `dimension` value, so a
compliant walk entry **cannot be written or validated as things stand**. `validate.py` would reject
it, correctly.

**Closing that gap is a schema change and therefore the operator's call**, not a documentation
choice: it means either a new dimension for verdicts or a decision that the walk's record lives
somewhere other than the change log — which would amend the ruling above. **Until it is closed**,
record the seven verdicts and the three floor answers as one file beside the review evidence in
`evidence/codex-scoped-<stamp>/`, so the verdicts and the report that prompted them stay together —
and treat that as a **stopgap the ritual is owed**, not as the design.

## Not part of this ritual

- **Selecting the next version.** That is [`FUNNEL.md`](FUNNEL.md), run in the same sitting.
- **Auditing middle-bucket cost claims.** FUNNEL.md proposes it as a fourth thing this sitting could
  do. It is **proposed, not ratified**, and is deliberately not in the checklist above.
- **Reviewing implementation.** A fresh per-task reviewer already covers that, and adding a second
  is the over-testing failure this ritual's placement rule exists to avoid.

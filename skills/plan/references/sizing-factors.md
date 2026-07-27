# Sizing factors — detail and worked examples

Five factors draw the boundary of a goal. Context budget is not one of them — it is the check
applied afterwards. The factors are applied in **precedence order**: outcome coherence is
primary; each subsequent factor refines the boundary the prior ones drew.

---

## Factor 1 — Outcome coherence

**Rule:** One deliverable — one thing that is *finished*. This is the primary factor; the others
refine it.

A goal produces exactly one outcome that can be called done on its own. If completing a goal
leaves something half-finished, the boundary is wrong.

**Test:** Can you write a single definition of done with one proving command? If you need two
unrelated proving commands, you have two goals (see Factor 4).

## Factor 2 — Kind of work

**Rule:** Research, implement, review, and judge are different kinds needing different agents,
different proving commands, and different provenance types. *"Research this then build it"* is
two goals however small.

This factor exists because the agent, the verification method, and the grounding kind all change
with the kind of work. A research goal produces a document grounded in sources; an implementation
goal produces code grounded in the spec. Mixing them in one goal means mixing provenance — the
result is neither properly researched nor properly built.

**Test:** Does the goal require the agent to switch modes — from investigating to producing, or
from producing to judging? If yes, split at the mode boundary.

## Factor 3 — Ownership

**Rule:** Doctrine-fixed (A8): research and paid calls are `research-agent`, exclusive. Work
spanning two owners is two goals even when tiny — **ownership beats size**.

This is the factor that overrides the budget floor. A goal that belongs to `research-agent`
cannot be merged with a goal that belongs to a different agent, regardless of how small either
is. The ownership boundary is a hard constraint from doctrine, not a sizing heuristic.

**Test:** Would two different agents need to execute parts of this goal? If yes, split at the
ownership boundary — even if one or both pieces fall below the 20K floor.

## Factor 4 — Verification boundary

**Rule:** One goal, one definition of done, one proving command. Two unrelated proving commands
means two goals.

The definition of done must be a single coherent assertion. If proving the goal requires two
independent checks that test unrelated properties, those are two separate outcomes wearing one
label.

**Test:** Write the gate-1 proving command. If you need `&&` joining two checks that test
different things (not two aspects of one thing), split.

## Factor 5 — Relationship

**Rule:** Work that must succeed or fail together is not split — partial completion would leave
an inconsistent state. Work where A must verify before B is sensible has its natural seam there.

This factor prevents both directions of error: splitting atomic work (leaving broken
intermediates) and merging sequential work (hiding a verification point).

**Test:** If the first half succeeds and the second half fails, is the first half usable on its
own? If yes, they can be separate goals. If no, they must stay together.

---

## The budget check (applied after the five factors)

After the factors have drawn the boundary, check the goal against the budget:

| Bound | Context bundle | Whole-loop | Action |
|---|---|---|---|
| **Floor** | — | 20K tokens | Merge it — **unless merging would cross an ownership or kind boundary** |
| **Default** | ≤ 40K (~150 KB) | ~64K | Normal — one deliverable, several files |
| **Ceiling** | 80K | ~128K | Look for a seam; signal the branch may be too coarse |

**Over the ceiling:** look for a natural seam — another outcome hiding inside. If there genuinely
is none, **read less rather than split**: tighter pointers, an index instead of whole files.

**Under the floor:** merge with an adjacent goal in the same branch — but only if they share the
same kind (Factor 2) and the same owner (Factor 3). If they don't, the tiny goal stands as-is.

All three numbers are starting values, revisable from run records. The floor is revisable too —
it is a heuristic with a documented origin, not a mechanism active in the runtime.

---

## Worked examples

### Example A — Ownership beats the floor

**Scenario:** A branch has two pieces of work:
- (a) Research which archive format the deployment target supports — estimated 8K tokens.
- (b) Implement the archive packaging using the chosen format — estimated 15K tokens.

**Naive merge:** Both are under the floor (20K individually), so merge them into one goal.
Total: ~23K, above the floor. One goal, one agent.

**Correct sizing:** Factor 2 (kind) says research and implementation are different kinds. Factor
3 (ownership) says research belongs to `research-agent`. These two factors override the floor.
Result: **two goals**, even though (a) is only 8K tokens.

- **Goal 1** (research, `research-agent`): "Determine the supported archive format for the
  deployment target." Definition of done: a committed document naming the format with evidence.
- **Goal 2** (implement, implementation agent): "Implement archive packaging in the chosen
  format." Definition of done: the packaging script produces a valid archive, proven by running
  it.

Goal 2 lists Goal 1 in its `blockedBy` — it cannot proceed until the research is done. Goal 1
lists Goal 2 in its `unlocks`.

### Example B — A goal above the ceiling with no natural seam

**Scenario:** A goal requires writing a single configuration schema that must be internally
consistent. The schema references six upstream specifications that total 90K tokens of context.

**Factor 1 (outcome coherence):** The schema is one deliverable — splitting it would produce two
halves that are each internally inconsistent.

**Factor 5 (relationship):** The two halves must succeed or fail together — a partial schema is
not usable.

**Action:** There is no natural seam. Instead of splitting, **read less**: provide an index of
the six upstream specs rather than their full text, with pointers to the specific sections
relevant to each part of the schema. This brings the context bundle under the ceiling without
breaking the outcome.

### Example C — Two outcomes hiding in one goal

**Scenario:** "Build the parser and write its test suite." Estimated 50K tokens.

**Factor 1 (outcome coherence):** The parser is one deliverable; the test suite is another. Each
can be called *finished* independently.

**Factor 4 (verification boundary):** Proving the parser works requires running the parser.
Proving the tests are correct requires running the tests and checking coverage. Two unrelated
proving commands.

**Action:** Split into two goals:
- **Goal 1:** "Build the three-format parser." Proving command: `python3 parser.py --test-input
  fixtures/` with exit code 0.
- **Goal 2:** "Write the parser test suite." Proving command: `pytest tests/test_parser.py` with
  exit code 0 and coverage above threshold.

Goal 2 lists Goal 1 in `blockedBy` — writing tests for a parser that doesn't exist yet is not
sensible.

### Example D — Atomic work that must not be split

**Scenario:** A database migration has two steps: add the new column, then backfill existing
rows. Estimated 35K tokens total.

**Factor 5 (relationship):** If the column is added but the backfill fails, the database is in
an inconsistent state — the column exists but contains nulls where it shouldn't. Partial
completion is not usable.

**Action:** Keep as one goal. The migration is atomic — it succeeds or fails as a unit.

---

## Anti-patterns

**Size-driven carving.** Splitting a goal to hit a token target rather than at a natural seam.
Produces goals cut at arbitrary byte boundaries — half a deliverable that cannot carry a coherent
definition of done. This is micro-tasking arriving by another road.

**Step lists as goals.** "1. Read the spec. 2. Write the parser. 3. Test it." This is a recipe,
not an outcome. Writing the agent's steps removes the reason to use an agent. The goal should be
"Build the three-format parser" — the agent decides how.

**Goals without stop conditions.** An objective with no stop is how an agent grinds or
fabricates. Every goal must state when it is done, not just what it does.

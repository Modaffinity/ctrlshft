# Review rounds

## What a round is

One dispatch of one advisor over one packet, returning findings. Two kinds, both required:

- **Codex round** — `ask-codex <packet directory> -- '<prompt>'`, from a subagent, **outside the
  command sandbox** (`ask-codex` cannot initialise inside one). The prompt is
  [The Codex prompt](INTERFACES.md#the-codex-prompt), sent verbatim. 🛑 **A blocked, missing or
  failing `ask-codex` is a stop condition, never a reason to fall back to the MCP `codex` tool.**
- **De-risk round** — a subagent takes the artifact's load-bearing assumptions and **runs**, for
  each, the smallest experiment that could falsify it, in the session scratchpad, reporting what
  happened rather than what would happen. Reasoning about a probe is not running it.

**Every round is a fresh advisor over a freshly assembled packet.** The packet is re-built from the
current artifact each round and its manifest sha256s prove which bytes were reviewed. A fixed
advisor was measured to produce three rounds of stale findings in a termination probe. The
orchestrator verifies every returned finding against the current artifact before it enters the
open-findings list; one that no longer reproduces is recorded as `stale` and closed with that
reason. Verification is a step, not a habit, because it is what kept that probe honest.

**Never treat an unavailable `ask-codex` as license to use `mcp__codex__codex` instead — that
substitution silently drops the containment the round exists to provide.**

| Excuse | Reality |
|---|---|
| "`ask-codex` is unavailable, so I'll use the MCP codex tool" | That is the measured failure this rule exists for. An unavailable `ask-codex` is `VERDICT: stop` — report the exact error and end the round, never route around it. |

Red flags — stop and re-read this section if you notice any of these in your own reasoning:

- the sandbox denies `ask-codex`'s state directory and `mcp__codex__codex` is sitting right there;
- "it's basically the same model, just a different call path";
- no operator is reachable and closing this out today feels urgent — that pressure does not change
  what a fenced tool is fenced for.

## Reading cannot detect a wrong fact about the machine

**A round is a reading.** An artifact can be internally consistent, fully reviewed and still wrong
about the environment it runs on. No number of readers finds that class — which is why one of the
two required round kinds **runs** experiments instead of reading them, and why "reasoning about a
probe is not running it" is written into its definition.

Any statement about how the machine behaves — whether a directory is private, what a command
prints, what a tool returns, what a folder contains — is carried as **measured** only if this run
ran it. Otherwise it is an assumption, and it belongs in the de-risk round's list.

Measured: a plan asserted that each task had its own private scratch directory. On the machine
there was one shared directory, and a task deleted a sibling's fixture. Three review rounds, a
revision and a fix pass all read that sentence. It was found by running two implementers at once.

This is [CHECKS.md](CHECKS.md)'s rule 1 aimed at a round rather than a check: a statement about the machine is measured only if this run ran it, or it is an assumption, not evidence.

## Classifying a finding

The test is mechanical, so that two readers agree:

- **blocking** — the artifact cannot be implemented by a fresh subagent with no memory of this
  conversation: a named file, path or symbol that does not exist; two sections that contradict each
  other; a placeholder; a missing interface between stages; an acceptance criterion that cannot be
  checked by running something.
- **advisory** — everything else: style, a better alternative, a risk without a defect, a suggestion
  that adds scope.
- **stop condition** — a blocking finding whose fix requires changing the brief's scope or
  philosophy, spend, reach beyond this pod, or an irreversible operation. It ends the round and the
  session; it is not a finding to rule on. If the only way to close a blocking finding changes the
  brief's scope, the verdict is `stop` and no ruling is written.

## The cap, and what happens at it

Blocking findings send the artifact back for [The revision dispatch](INTERFACES.md#the-revision-dispatch),
and a further round runs against the revision. 🛑 **Three rounds per artifact, counting both advisor
kinds — three in total, not three each.** The default allocation is round 1 Codex, round 2 de-risk,
round 3 a targeted re-check of the revision by whichever kind the open findings call for; the
orchestrator may re-allocate but never exceed three.

At the cap the orchestrator rules on each residual blocking finding itself
(`Ruling: <decision> — <why> — <what it costs if wrong>`), records every residual finding of both
classes in the ledger **and** in the final report, and proceeds. It does not run a fourth round and
does not ask the operator. One exception: a residual finding it cannot rule on because either ruling
changes the brief is the stop condition above, not a ruling.

A revision made after the last round is verified by the orchestrator against the open-findings list
rather than by an advisor — that is what "rule and record residuals" means, and every such residual
is named in the report.

**Never buy a fourth round.** Three is the cap whether or not the open finding feels close to
closed.

| Excuse | Reality |
|---|---|
| "One more round would close it" | Three rounds per artifact, counting both kinds. At the cap you rule and record — you do not buy a fourth, however close the last round looked. |

Red flags — stop and re-read this section if you notice any of these in your own reasoning:

- you are on round 3, the finding looks almost closed, and a fourth round feels cheap;
- the advisor is deterministic or scripted and "one more call costs nothing" reasoning follows from
  that;
- there is no `STATE.md` yet — its absence is not permission to skip the ledger entry the cap
  requires once it exists.

⚠️ `evidence/` is gitignored in a CortexOS pod, so an `ask-codex` evidence folder is **not** a
tracked record — a fresh clone does not have it. Each round's findings are written into `STATE.md`'s
ledger, which is tracked, with the evidence folder named as a pointer. Otherwise the "reviewed"
record is something a fresh clone cannot see.

## The advisor packet

**How a path resolves, everywhere below.** A relative path resolves against the directory of the
file that names it; a path beginning `~/` or `/` resolves as written. **Link syntax inside a fenced
block or an inline code span is not a link** — a document that quotes a path yields a phantom
dependency, not a real one. A target that does not resolve is **never dropped silently**:
`MANIFEST.md` records it as `unresolved: <path> (named by <file>:<line>)`.

**A file's dependencies in a markdown-and-shell deliverable are:**

1. every markdown link `[text](path)` whose target resolves to a file that exists;
2. every `@`-reference (`@path/to/file`);
3. in a shell script: every `source`/`.` target, every script invoked by a path resolving inside the
   pod or inside `~/dotfiles`, and every file path appearing as an argument literal;
4. in a Python script: every `import` resolving to a file in the repo, and every string literal that
   resolves to an existing path;
5. every frontmatter field whose value is a path (`brief:`, `research:`, `sources:`, `spec:`); a
   value resolving to a **directory** contributes every `.md` directly inside it;
6. a file named by **basename only in backticks**, resolved by exact-basename search over
   `git ls-files` from the pod root, **excluding** `.claude/`, `.superpowers/`, `evidence/`,
   `outputs/`, `inputs/`, `node_modules/` and `subprojects/`. **More than three matches means
   ambiguous**: none of them enter the packet, and the manifest records
   `ambiguous-basename: <name> (<n> matches)`;
7. every absolute path under `~/dotfiles/` in backticks that resolves to an existing file; such a
   path naming a directory contributes its direct `.md`, `.py` and `.sh` children, and a `{a,b,c}`
   brace expansion is expanded before resolution;
8. a bare skill name in backticks that resolves to `<root>/<name>/SKILL.md` for `<root>` in
   `~/dotfiles/skills/`, `~/.claude/skills/`, or the installed superpowers plugin's `skills/`
   directory.

**Rules 6–8 exist because of measured failures.** Unbounded, rule 6 pulled 36 junk files —
`.claude/settings.json`, `.superpowers/sdd/**`, `evidence/**` and every `README.md`, `CLAUDE.md` and
`AGENTS.md` in the pod — into a single packet. Rules 7 and 8 exist because without them a packet for
a deliverable living in `~/dotfiles` missed the command files the artifact edits, the eleven retained
v1 files, and the `test-driven-development` skill it invokes: rule 6's basename search is scoped to
the pod's own `git ls-files` and cannot see a file that exists only in `~/dotfiles`, so only rule 7's
absolute-path form and rule 8's skill-name form reach files outside the pod at all.

**The packet contains**, confirmed against `MANIFEST.md` as a checklist before dispatching — not a
prose reminder to be skimmed:

- [ ] the artifact under review;
- [ ] `plans/<slug>/BRIEF.md`;
- [ ] every file in the artifact's dependency set (level 1);
- [ ] every file in the dependency set of each level-1 file (level 2) — the one level of closure
      beyond what the artifact names, and the level whose absence let a fixture idiom survive two
      reviews.

## Overflow

**Cap: 50 files or 500 KB, whichever binds first.** A 41-file packet was measured to run through
`ask-codex` without trouble, so the cap sits just above the only size measured to work.

On overflow, files are dropped in tier order — the earlier tiers are dropped last:

| Tier | What is in it | Dropped |
|---|---|---|
| A | the artifact and `BRIEF.md` | never |
| B | level-1 files reached by rules 1, 2, 5 — the artifact links them explicitly | third |
| C | level-1 files reached by rules 3, 4, 6, 7, 8 — inferred from contents or from a name | second |
| D | every level-2 file | first |

Within a tier, drop in ascending order of how many packet files depend on the file, ties broken by
descending file size. **Name every dropped file in the manifest**, with its tier and the count that
placed it — a silent drop is precisely the failure this rule exists to prevent.

**`cap-exceeded`.** The spec's clause is narrow — it fires only when tier A alone exceeds the byte
cap. The shipped `advisor-packet.py` broadens it: `cap-exceeded` fires whenever any tier B or C
(level-1) file is dropped, or the kept set is still over either cap after dropping everything
droppable. A tier D drop is level 2 and by design; a tier B or C drop means the packet no longer
carries the one level of closure the brief promises, which is the failure the flag exists to name.
The narrow form was measured unreachable in practice: on this package's own review packet, cutting a
192-file closure down to 21 to fit the byte cap dropped 171 files — 37 of them level-1 tier C — and
raised nothing, because tier A alone never exceeded the cap — a gate that cannot fail, [CHECKS.md](CHECKS.md)'s rule 1 turned the other way.

If tier A alone exceeds the byte cap, the round still runs and the manifest still records
`cap-exceeded`: the artifact plus the brief is the minimum viable packet, and refusing to review is
worse than reviewing a large one.

## Cross-repo packets

`ask-codex` refuses a path resolving outside the current repo. When the deliverable under review
lives in `~/dotfiles` while its workstream lives in this pod, the packet has to be assembled on this
side:

```
scripts/advisor-packet.py <artifact> --brief <path> --out plans/<slug>/notes/packet-<artifact>-r<N>/
```

This copies the packet into the pod, writes `MANIFEST.md` naming each file's source path and sha256,
and the round names that directory to `ask-codex`. A dependency that resolves outside both the pod
and `~/dotfiles` is not copied and is recorded as `out-of-reach` in the manifest.

Afterwards, the **orchestrator** deletes the copied packet files in the same between-stages step
that writes the round's ledger block, and commits `MANIFEST.md` with it. The copies are scratch;
the manifest is the tracked record.

## The Coverage pass

**Not a round.** It runs before round 1, at the first step of B3, and again at the first step of
B5. It does not spend one of [the cap](#the-cap-and-what-happens-at-it)'s three. It takes the shape
[the revision dispatch](INTERFACES.md#the-revision-dispatch) already defines: its own dispatched
subagent, `findings` kind, model `standard`, ledgered under its own heading —
`### Stage B3 — <stage name>, Coverage pass (not a round) · <verdict> · <date>`. **What it reads:**
`BRIEF.md` and the artifact, nothing else. **What it writes:** nothing — it reports, it does not
repair.

**The brief's Constraints are the requirement list.** *Research used* and *Decisions settled* are
provenance, and demand nothing.

**Stable keys on both sides.** The spec carries one canonical `C<n>` key table, one row per key, in
the brief's order, naming the heading that satisfies it. **The pass reads that table as a table,
never greps a key** — `\bC1\b` matches `C11`, and `\b` behaves differently under BSD and GNU `grep`.
It then verifies each row's cited heading exists in the artifact — otherwise an artifact could
satisfy the table by writing the table.

**What it returns:**

```
ARTIFACT: none
COVERAGE: <n> of <n> constraints covered

| key | status | where |
|---|---|---|
| C1 | covered | § 4 |
| C7 | ruled | § 8.1, Ruling R6x |
| C9 | UNCOVERED | — |

BORROWS: <n> of <n> named sources placed
| source | what it said to take | where it landed |
|---|---|---|

VERDICT: done | blocked | stop

FINDINGS:
- [blocking] <key> is UNCOVERED — nothing in <artifact> points at it
```

Three statuses, no fourth: `covered` (a section of the artifact satisfies it — cite the section,
never a line number, because lines move), `ruled` (a Ruling in the artifact drops it, cited), and
`UNCOVERED` (nothing to point at). Every `UNCOVERED` row is one **blocking** Finding, closed either
by the artifact covering it or by a Ruling dropping it on the record. **Forgetting is never a
reason.**

**Its own empty case.** `COVERAGE: 0 of 0` means the pass could not read the brief's Constraints
section and is a `blocked` verdict, never a clean pass.

**At B5, one substitution.** The plan satisfies a Constraint when at least one task's requirements
name the spec section that Constraint's row points at — spec-kit's Pass E, *requirements with zero
associated tasks*. The finding cap is borrowed and not taken: fourteen Constraints cannot overflow,
and a cap on a fourteen-row walk would hide the one row that matters.

**The second table, `BORROWS`.** One row per source named in `BRIEF.md` § *Research used*. A
`not taken — <reason>` row is lawful; a **missing** row is the defect — and it is **advisory**, not
blocking, since provenance demands nothing. What this ends is the *silent* absence.

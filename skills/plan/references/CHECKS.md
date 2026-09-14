# Checks

A check that cannot fail and a gate that cannot pass are the same defect from opposite ends: rule 1
below is what makes a check able to fail, and rule 2 is what makes a gate able to pass.

## 1. A check states what it returns when the thing IS there

**A check whose failure mode is silence is the one to distrust.** `grep -c` returns `0` both when
it measured and found nothing and when it measured nothing at all. Nothing in the output tells the
two apart, and they are opposite in meaning.

**Before a check is written down:** name the file that writes the string it looks for, and the task
that requires that string to be written. If neither exists, the anchor is wrong — not the
expectation. A check must be anchored to a string the deliverable actually writes.

**Before a check's result is believed:** run the same check for something you know is present. That
is the **positive control**. If the control also comes back empty, the check is broken, not the
record. Report the control beside the result.

**And the control must exercise the same construct the check depends on.** A control is itself a
check, so it inherits this whole rule — including the part about failing. Name the construct the
check leans on — an alternation, a multi-pattern invocation, a recursive walk, a field join, a
range, a regex class — and make the control exercise **that**, on a string you know is present.
A control that drops the construct proves only the part that was never in doubt.

Two shapes that look like controls and are not:

- **A control weaker than the check.** A plain literal used to control an alternation proves the
  walk reached the files and says nothing about the pattern. It passes while the check is broken.
- **A control that returns nothing when it passes.** "The same command for a string known *absent*
  returns 0" is satisfied by a command that never ran. A positive control returns **hits**, and you
  read the hits.

Where the check matches several alternatives, put the known-present one **last**. A first-position
control passes on an implementation that reaches only the first alternative.

**A check can contaminate its own evidence.** Where the thing being counted is a string, and the
search itself is recorded — a transcript, a log, an audit trail, a file the tool also writes to —
running the check writes the anchor into the corpus the check reads. Measured: grepping a session
transcript for an agent-completion anchor put that anchor into the transcript of the agent doing
the grepping, so a later raw count of the same file returned 2 where the true answer was 0. The
answer is not to stop looking: **count by record structure rather than by raw string**, and where
only a string is available, exclude the searcher's own records by name and say that you did.

**The same test applies one level up, to assumptions.** A sentence about how the machine behaves —
that a directory is private, that a command exits 0, that a folder contains a thing — is carried as
*measured* only if this run ran it. Otherwise it is an assumption.

Measured: fourteen checks in one release returned clean, plausible numbers and measured nothing.
**Every one was found by running it. None by reading it.** One of them manufactured a pass rather
than merely failing to catch.

| Shape | What it actually measured |
|---|---|
| an ERE alternation written inside a markdown table cell, its pipes backslash-escaped so the table parses | one literal string. In ERE a backslashed pipe is a **literal pipe**, so the alternatives are never alternatives. Measured on BSD grep 2.6.0: 0 hits against a file containing `TBD`, 1 without the backslashes. In **BRE** the same escape *is* alternation — which is why the defect survives being read |
| a positive control that drops the check's alternation — one plain literal, to prove a multi-pattern grep | the **walk**. It returns hits while the check itself matches nothing |
| `grep -c '^## '` over a reference | headings **inside a fenced template**, inflating the count |
| `git log <first>..<last>` | a two-dot range **excludes** `<first>` |
| `git log --merges` as a landing verdict | `0` for a branch that fully landed — a fast-forward makes no merge commit. Use `git merge-base --is-ancestor` |
| counting a child's tool calls in the **parent's** transcript | the records are not there; the `0` meant **absent**, not zero |
| `until ls A B C` as a waiter | `ls` fails unless **every** operand exists — "when any lands" became "when all land" |

## 2. A gate a correct artifact cannot pass is rescoped and reported, never waived

A check that cannot fail and a gate that cannot pass are the **same defect from opposite ends**.
Both still report a result, and the result means nothing.

**The rule.** Every mechanical gate is scoped to what the run itself changed, and the number it
would have produced unscoped is published beside it. Rescope by intersecting the gate's findings
with the run's own diff, or exempt the class **by name in the checking code**. Never waive by an
argument passed at run time: an argument leaves no record and has to be re-decided every run.

**Why not a strict gate plus a waiver.** The build session runs unattended. Nothing stops a stage
overriding its own gate except that overriding is not normal there. A gate that fails on a
*correct* artifact makes overriding normal on the very first run, and every session after inherits
the habit — so the gate stops measuring what it was written for and starts measuring nothing, while
the run still reports passing it. That is worse than having no gate.

**The test, before a gate is written:** name the artifact that is *correct* and ask whether it
passes. If it does not, the gate is wrong.

**Two classes are exempt by construction, and both are named in code rather than waived:** a file
appended to by contract, and a workstream's own artifacts, whose length is a function of the work
they record rather than of how readable they are as doctrine.

**What this costs, stated rather than hidden:** debt a run did not introduce reaches the base
branch unblocked. The published unscoped number is what keeps that from being silent.

Measured: this pattern surfaced five times in one release, three of them in artifacts that had
already passed a full review.

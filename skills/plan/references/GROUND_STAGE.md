# Ground — B1's procedure

B1 confirms or creates `ARCHITECTURE.md` at the pod root before any later stage reads it. Named as
its own reference rather than a section of `BUILD_SESSION.md` (ruling R61): `BUILD_SESSION.md` loads
for every one of the nine stages, and B1 is the one stage with no superpowers skill behind it, so it
gets a manual rather than a row.

## 1. The decision, with no third branch

Does `ARCHITECTURE.md` exist at the pod root?
**No → create it.** Not skip, not ask, not defer to the operator. The build session is unattended
(`ADR 0003`); there is nobody to ask, and a skipped stage returns `done` over an absence.
**Yes → run the freshness test below.**

## 2. The template

Matklad-shaped per `ADR 0002`, carried here as a fenced block rather than a sentence, because *this
exact template was lost once before* — named in a brief, absent from a spec, `C10`'s founding
incident. A list inside a sentence is easy to drop a member of; a block is not:

```markdown
# Architecture — <the system this pod builds>

## Bird's-eye view
## Code map                 <!-- the pieces, and where each one lives -->
## Invariants
## Conventions
## Where this piece sits    <!-- the neighbouring pods, and the control-plane map -->
```

Under 300 lines. It describes **the system the pod builds, never the pod's folder layout** — that
is `README.md`'s job, and conflating them is how the document reaches 800 lines nobody reads.

## 3. The freshness test

B1 of this workstream is the only field data so far, and it surfaced a weakness: its reach list was
derived once, by one reader, and omitted `SKILL.md` (`STATE.md` § Stage B1, advisory 3). This
procedure closes that with a second **mechanical** source rather than a second reader:

1. Derive the reach list from **`BRIEF.md`'s Constraints**, and **write it down before opening
   `ARCHITECTURE.md`.** A list derived while reading the document under test is a test that cannot
   fail.
2. Derive a second list mechanically: `git diff --name-only <base>...HEAD`, plus every path named
   in the brief's *Scope*. Take the **union** of the two. One reader's judgement is not the list.
3. For each entry, `command grep` for it in `ARCHITECTURE.md`. Record named / unnamed.
4. **Positive control.** Run the same grep for a string you know the document contains — a section
   heading. If the control also returns nothing, the grep is broken and the coverage figure means
   nothing. Report the control beside the result.
5. Every unnamed piece gets a line. The document is then fresh. **The empty case:** "zero unnamed
   pieces" is a pass **only if step 4's control passed**.

## 4. The `blocked` path

Three triggers, named so the call is never a judgement:

- the pod root is not writable
- the pod's `.gitignore` denies the path and the `!` line cannot be added
- the pod has no identifiable system that it builds

Return `blocked`, naming which. `blocked` is the stage saying *I could not*, and it is the only
lawful alternative to creating.

## 5. A stale fact is not a stale document

Ruling R57. The freshness test measures **coverage**. A factual error found while running it — a
sentence about the world that is no longer true — is an **advisory** finding routed to B7, which
owns this file as its item 1. B1 does not fix it: its single edit would land before the work that
changes it, and B7 would rewrite the same lines twice.

## 6. What B1 does not do

Ruling R58. It does not read outside the pod, and *"every top-level piece this branch touches"*
means pieces that exist now — never artifacts the workstream has not designed yet.

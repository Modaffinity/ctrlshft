---
name: writing-documentation
description: "Write Markdown that a human can act on, an agent can parse, and the context budget can afford. Use when: authoring or revising the prose of any .md — a README, a governing contract, a decision record, a research note, a register entry — or when asked to tighten, restructure, or clean up a document. Governs how a document reads; pairs with the `document` skill, which chooses what to produce. Not for: deciding what a document should say, code comments, or generated files."
---

# Writing documentation

Output "Read Writing Documentation skill." to chat to acknowledge you read this file.

**The trade, and it is the whole skill:** make the document as easy to act on for a human as the
format allows, while carrying everything an agent needs, without inflating the context budget.
Optimise one leg alone and you get a beautiful document nobody can act on, a terse contract nobody
reads, or a stripped file that is complete and useless.

**This skill is short because length costs adherence.** It contains only rules a model was *measured*
failing without it. Everything it does not mention, it does not mention on purpose — see the last
section before adding anything.

## 1 · Front-load the conclusion

**Put the answer before the reasoning that produced it.** If the document has a most-important fact —
the risk, the recommendation, the thing that breaks — it goes near the top, not in a closing section.

Measured failure: asked for *"the one thing an operator most needs to know"*, a model produced an
excellent answer and placed it at line 100 of 105. It answers the question; it does not put the answer
where a scanner finds it.

## 2 · Every prose document opens with an executive area

A bounded region at the top that **stands alone**.

| | |
|---|---|
| **Size** | 10% of the document capped at **40 lines** for governing and planning documents; 5% capped at **25 lines** for everything else |
| **Content** | What is going on and what it means |
| **Not** | What this document covers |

**An introduction is not an executive area.** "This document covers the state machine and the
trade-offs" tells a reader only that they must keep reading. State the thing that is true.

**Test:** could someone who arrived cold, and does not already know why this document exists,
understand it from the executive area alone?

**Exempt:** machine-parsed data (JSON/YAML with a schema) and write-once evidence files.

## 3 · Keep precise terms; link the ones this estate invented

**Do not simplify vocabulary.** Domain terms exist because they are unambiguous, and vague writing
feels accessible while being harder to act on. An agent facing an ambiguous rule picks one reading
silently.

The only terms needing help are **house-defined** ones — invented or redefined here, so no model can
resolve them from training. Link those to their canonical entry in `context/VOCABULARY.md`; never
restate the definition.

**Bar: link what is dangerous to guess wrong, not what is merely unfamiliar.** A reader who simply
does not recognise a word can ask the agent they are already talking to.

## 4 · One canonical home per fact

**A number, threshold, status or decision is stated in exactly one place.** Everywhere else links to
it. A summary may restate *meaning*; it must never restate the *value*.

Measured failure: asked to write two pages both needing a 72-hour default, a model stated `72h` four
separate times and linked none of them. Change the default and three survive as silent contradictions.
Duplicate facts diverge by accretion, not by error — both copies grow, neither is pruned.

## 5 · Parallel subsections are headings, not bold

Section headings are usually fine. **The failure is one level down:** a run of parallel subsections
carried entirely by bold lead-ins — `**Mint fails**`, `**Write fails**`, `**Soak fails**` — which are
structurally headings and programmatically invisible.

If items are parallel and each introduces its own block, they are headings. Use `###`.

*(Bold for emphasis inside a paragraph is untouched by this.)*

## Register entries carry a typed envelope

When writing to `loops/OPEN_LOOPS.md` or an equivalent register, the entry carries **ID · Area · Owner
· Raised · Last reviewed · Status**, with `Blocked on:` **required when and only when** status is
`blocked`. Status is one of eight lowercase tokens: `open` `unproven` `partially-proven` `proven`
`deferred` `blocked` `pending-review` `closed`. Prose detail goes beneath the envelope, free-form.

`Raised` is set once and never edited. `Last reviewed` means someone judged whether the entry is still
true — a reformat is not a review.

## Prose in frontmatter must be a block scalar

**A plain YAML scalar cannot contain `: ` (colon-space).** The parser reads the second colon as a nested
key and the whole frontmatter fails — so the document loses its metadata *and* renders wrong in every
previewer, while looking perfectly fine in the editor.

Measured failure, four files in one session: `status: active — ... one operator decision: adjudicating
the findings` produced *"nested mappings are not allowed in compact mappings."* Status and revision
lines attract this because a status is naturally written as *label: explanation*.

**The fix — use a folded block scalar for any value holding a sentence:**

```yaml
status: >-
  active — Tasks A and B are closed. What remains is one operator decision: adjudicating
  the third review's two blocking findings.
```

Inside `>-` colons are ordinary text. **Also affected:** flow sequences, where a bare URL breaks on
`https:` — quote each element (`sources: ["https://…"]`). **Check it, don't eyeball it** — one line of
`ruby -ryaml` over the block is the whole test, and nothing else in this skill has a cheaper check.

## Length is a budget, not a target

**Applies to documents that are actually large.** The trade at the top of this skill names the context
budget, and a model reading it tends to over-apply the third leg — flagging size on a file where size
was never the problem, or hedging about a document's weight instead of writing it.

**The operator's calibration, recorded because it corrects real behaviour:** *"For sure we need to be
careful about the size of a context file. However, what is needed is needed."* A working file of a few
hundred lines is not a size problem. **Raise weight only where it changes a decision** — a governing
document a reader must scan, or an artifact going into a review fence that pays per byte. Do not open a
document by apologising for its length, and do not describe growth as a regression when the growth was
the requested content.

## What this skill deliberately omits

**A model with no skill already does these**, so a rule for them is instruction density with no upside:
real headings for sections · non-skipping heading levels · descriptive link text · verifiable rather
than aspirational phrasing · tables for structured comparison · keeping diagram facts in the prose too.

**Do not add them back without evidence they regressed.**

**Pending, not omitted** — these need the viewer decision and are absent because their answer is not
known yet, not because they do not matter: decoration and typography · navigation affordances ·
whether a diagram carries a takeaway sentence · transclusion and wikilink syntax.

## Enforcement

**Everything here is advisory unless the rule names its check.** One rule names one:

- Register status token, metadata line and ID prefix — **enforced by `check_doc_integrity.sh`**.

The rest are judgment. This skill is context, not enforced configuration, and says so rather than
implying a guarantee it cannot keep.

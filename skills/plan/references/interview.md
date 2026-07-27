# Interview — discipline rules and question design

The discovery loop owns its interview (Step 1b). It proceeds through three sequential postures
— Build, Complete, Attack — and applies `grill-me`'s interviewing discipline as text in the
Attack posture. This file holds the discipline rules and the question-design constraints the
spine references but has no room to detail.

---

## The three discipline rules (from `grill-me`)

These are adopted as text for the Attack posture. They are interviewing discipline — how to ask
well — and they are the reason `grill-me`'s contribution survived the decision to own the
interview rather than call it.

### 1. Sharpen fuzzy language

> *"You're saying 'account' — do you mean the Customer or the User?"*

When a term is ambiguous, force a choice. Adjectives without quantification ("robust",
"intuitive", "fast") are the most common form: replace each with a measurable condition or
remove it. A requirement stated as an adjective cannot be proven done — it cannot become a
gate-1 proving command.

**Action in the loop:** When the Attack posture finds a fuzzy term, it does not just flag it —
it proposes a concrete replacement and asks the operator to confirm or correct. The answer is
written back to the decision register or the assumption register, depending on whether it is a
choice or a belief.

### 2. Invent concrete boundary scenarios

Create specific edge cases that force precision about boundaries. Not "what happens on error?"
but "the upload is 2.1 GB and the limit is 2 GB — what does the user see?" Concrete scenarios
reveal the assumptions hiding behind general statements.

**Action in the loop:** Each scenario is stated as a concrete situation with a proposed answer.
If the answer reveals an assumption, it is recorded in the assumption register with its
provenance and confidence. If the answer reveals a decision, it goes to the decision register
with implications.

### 3. Cross-reference against the repo

> *"Your code cancels entire Orders, but you just said partial cancellation is possible — which
> is right?"*

Hunt contradictions between what the operator says and what already exists — in code, in
documentation, in prior decisions. The repo is the ground truth for what *is*; the operator is
the authority for what *should be*. When they conflict, the conflict is surfaced, not silently
resolved.

**Action in the loop:** When a contradiction is found, state both sides and ask the operator to
resolve it. If the resolution overrides existing code, record it as a decision with the
implication that the code must change. If the resolution confirms the code, record it as a
decision that the stated requirement was wrong.

---

## Three postures, in order

The interview is not a single mode — it is three sequential phases, each with a different
purpose and a different failure it prevents.

### Build (posture 1)

**Precondition:** An idea with no design yet.
**Motion:** Additive — generate the vision. Run the coverage taxonomy, propose approaches,
synthesise a design from the operator's answers. Constructive.

**Failure it prevents:** Starting decomposition without a vision. A vision that was never
generated is worse than one that was generated and attacked — the first contains only what the
operator happened to say, not what they would have said if asked.

**Stops when:** A draft vision exists — even if incomplete. The next posture fills the gaps.

### Complete (posture 2)

**Precondition:** A draft vision with gaps.
**Motion:** Fill — scan for underspecification. Find ambiguous adjectives lacking quantification,
missing completion signals, undefined terms, implicit assumptions, unstated dependencies. Encode
answers back into the artifact.

**Failure it prevents:** Proceeding with a vision that has gaps visible only to someone who
reads carefully. The coverage taxonomy (Step 1c) drives this scan — it is structured, not
ad hoc.

**Stops when:** Every coverage category is Clear or the remaining Partial/Missing categories
have been explicitly deferred (because the answer is needed at branch level, not vision level).

### Attack (posture 3)

**Precondition:** A vision that looks complete.
**Motion:** Subtractive — stress-test before committing to decomposition. Apply the three
discipline rules above. The point is to break what was built, not to add more.

**Failure it prevents:** Committing to a decomposition on a vision that contains contradictions,
untested assumptions, or fuzzy language that will produce different interpretations in different
branches.

**Stops when:** The remaining challenges do not change the branch map or wave order — they are
detail-level, deferrable to the relevant wave. This is the "the carve would be right" stopping
rule from Step 1g.

---

## Question-design rules

These rules govern how questions are constructed, regardless of which posture generates them.

### Hard cap: 8 questions per round

Each round surfaces at most 8 questions. If more than 8 categories remain unresolved after
filtering, rank by Impact x Uncertainty (see `references/coverage-taxonomy.md`) and take the
top 8.

### One at a time

Ask one question, wait for the answer, write it back, then ask the next. Never present a batch.
The reason is practical: each answer may change which question comes next.

### Pre-filled recommended answer

Every question includes a recommended answer — the planner's best guess, stated explicitly.
The operator can accept, modify, or reject it. This is faster than open-ended questions and
surfaces the planner's assumptions for correction.

### Answerable format

Each question must be answerable by:
- 2–5 option multiple choice, **or**
- A short answer (a few words, not a paragraph).

Open-ended questions are rewritten until they meet this bar. If a question cannot be made
answerable, it is a sign that more research is needed — call `research`, not the operator.

### Exclusion rule

A question is excluded if the answer would not materially change the decomposition, the
definition of done, or the wave order. This prevents the interview from becoming exhaustive
rather than targeted. Detail questions belong in the wave that details the relevant branch.

### Never reveal queued questions

The operator sees one question at a time. Revealing the queue biases answers and wastes
attention on questions that may become irrelevant after earlier answers.

### Stop early

End the interview when critical ambiguities are resolved or the operator says done. The goal
is "the carve would be right" — not "everything is known."

---

## Write-back

Every answered question is immediately written into the plan artifact:
- A **choice** goes to `decisions.md` with why and implications.
- A **belief** goes to `assumptions.md` with provenance, confidence, and dependents.
- An **open question** that cannot be answered now goes to `questions.md` with what would
  resolve it.

An interview whose output lives only in the transcript is lost at session end.

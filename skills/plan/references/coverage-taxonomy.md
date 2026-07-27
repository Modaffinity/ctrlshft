# Coverage taxonomy

The discovery loop runs a structured coverage scan during the **Build** posture (Step 1b.1).
For each category below, mark **Clear / Partial / Missing** and use the map to decide what to
ask. Questions are generated internally from this scan — never from ad-hoc curiosity.

This taxonomy derives from spec-kit's `clarify` command (MIT), adapted for planning rather than
specification clarification. The original eleven categories are retained; examples and filtering
rules are plan-specific.

---

## The eleven categories

### 1. Functional scope and behaviour

What the system does — its verbs. Look for: named operations, user-facing actions, processing
steps, transformation rules.

**Example signals of Partial/Missing:** "it should handle uploads" (which formats? what size
limits? what happens on failure?); a verb with no object; an action with no completion condition.

### 2. Domain and data model

The nouns — entities, their attributes, relationships, cardinality, lifecycle states. Look for:
implied entities never named, relationships with unstated cardinality, lifecycle transitions with
no trigger.

**Example signals:** "users have accounts" (1:1? 1:many? what creates an account?); an entity
mentioned in one context with a different name in another.

### 3. Interaction and UX flow

How users (or callers) interact — entry points, sequences, feedback, error presentation. For
non-UI projects: the API contract, CLI interface, or integration protocol.

**Example signals:** a described workflow with no error path; "the user sees a confirmation" with
no specification of what they confirm or how they cancel.

### 4. Non-functional quality attributes

Performance, reliability, scalability, security, observability, accessibility. Only those that
would change the decomposition or the definition of done — not a checklist to fill.

**Example signals:** "it should be fast" (what latency? measured where?); no mention of
authentication on a user-facing system; no mention of logging on a production service.

### 5. Integration and external dependencies

What the system connects to, what it expects from those connections, and what happens when they
fail. APIs, databases, third-party services, file systems, message buses.

**Example signals:** a named external service with no failure mode; "calls the API" with no
mention of auth, rate limits, or versioning.

### 6. Edge cases and failure handling

What happens at the boundaries — empty inputs, concurrent access, partial failures, timeouts,
malformed data. The attack posture (Step 1b.3) stress-tests these, but the scan identifies which
areas lack any edge-case consideration.

**Example signals:** a happy path described in detail with no mention of what happens when it
fails; batch processing with no mention of partial failure.

### 7. Constraints and tradeoffs

Hard constraints (budget, timeline, technology mandates, regulatory) and acknowledged tradeoffs
(consistency vs availability, simplicity vs flexibility). These directly affect the branch map and
wave ordering.

**Example signals:** a technology choice with no stated reason; "we must use X" with no mention of
what X costs or prevents.

### 8. Terminology and consistency

Do the same terms mean the same things throughout? Are domain terms defined? This catches the
"account means three different things" class of ambiguity before it produces branches that
contradict each other.

**Example signals:** a term used in two contexts with subtly different meanings; an acronym
introduced without expansion; different words used for the same concept.

### 9. Completion signals

Acceptance-criteria testability and measurable definition-of-done indicators. This is the gate-1
proving command at the requirement level — if a requirement cannot be proven done, it cannot
become a goal.

**Example signals:** "the feature is complete" with no definition of complete; "users can log in"
with no specification of what constitutes a successful login; requirements stated as adjectives
("robust", "intuitive") rather than measurable conditions.

### 10. Stakeholders, owners, and approval paths

Who decides, who approves, who is informed, who owns the result. Affects the autonomy class in
guardrails, the operator gate, and whether a judged gate is needed.

**Example signals:** no named owner for a deliverable; "the team reviews" with no specification
of which team or what constitutes approval.

### 11. Existing assets, prior art, and constraints from the repo

What already exists — code, documentation, prior attempts, patterns established in the codebase.
The attack posture cross-references claims against the repo; this category identifies what to
cross-reference.

**Example signals:** a feature described as new that the repo already partially implements; a
design that contradicts an established pattern with no acknowledgment.

---

## Filtering rules

A question generated from the taxonomy is included **only if** all of the following hold:

1. **Material impact.** The answer would change the decomposition (branch boundaries), the
   definition of done (what proves a goal complete), or the wave order (which branch goes first).
   If the answer would not change any of these three, the question is excluded.

2. **Not deferrable.** The answer is needed at vision level, not at branch-detail level. Questions
   about detail inside a branch are deferred to that branch's wave — asking them now is the "too
   deep" failure mode (Step 1g).

3. **Answerable.** The question can be answered by 2-5 option multiple choice or a short answer.
   Open-ended questions are rewritten or split until they meet this bar.

4. **Not already resolved.** The answer is not already available in the context, the repo, or a
   prior answer in this session.

---

## Ranking: Impact x Uncertainty

When more than 8 categories remain unresolved after filtering, rank the surviving questions by
**Impact x Uncertainty** and take the top 8:

- **Impact** = how much the answer changes the branch map or wave order. High: changes which
  branches exist or which goes first. Medium: changes goals within a branch. Low: affects
  implementation detail only (and should have been filtered out).

- **Uncertainty** = how confident the planner is in the default answer. High: no basis for a
  recommendation. Medium: a recommendation exists but depends on an ungrounded assumption. Low:
  the recommendation is well-grounded.

The product is the priority. A high-impact, high-uncertainty question always outranks a
medium-impact, medium-uncertainty one. Ties are broken by category order (1-11) — earlier
categories affect more downstream decisions.

---

## How the scan fits the interview flow

1. **Before asking anything**, run the scan silently. Mark each category Clear / Partial / Missing.
2. **Generate questions** from Partial and Missing categories, applying the filtering rules.
3. **Rank** by Impact x Uncertainty, cap at 8.
4. **Ask one at a time**, with a pre-filled recommended answer.
5. **Write back** each answer immediately (Step 1e) — the scan's output lives in the artifact, not
   only in the transcript.
6. **Re-scan** after each round. Categories that moved to Clear are done. New Partial categories
   may emerge from answers. Stop when critical ambiguities are resolved or the operator says done.

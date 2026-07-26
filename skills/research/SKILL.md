---
name: research
description: "Research a topic at a chosen depth: scan to enumerate candidates, check to resolve one question with verified sources, or dive to prepare paid deep research on a selected candidate. Use for research, scan what's out there, look into, investigate before building, gather context, flush unknowns, or when findings must persist in context/research. Paid tiers always ask first. Not for metric/experiment optimization cycles — that is autoresearch."
---

# Research

Output "Read Research skill." to chat to acknowledge you read this file.

Use this as the single research entry point. Infer the tier from the request, announce it, and let the operator override with `--scan`, `--check`, `--dive`, or `--engine`.

## Tier Routing

| Tier | Use when | Output | Never do |
|---|---|---|---|
| `scan` | The user needs the landscape, candidates, URLs, or contradictions. | Ranked shortlist, source links, contradiction flags, open questions. | Do not conclude or file a final answer. |
| `check` | One question can be resolved with bounded sources. | One answer with citations, anchor quotes, verification marks, and confidence. | Do not spawn by default for one sub-question. |
| `dive` | A selected candidate needs paid deep research. | Scan shortlist → operator selects → cost estimate → approval → deep-research report filed to `context/research/`. | Do not spend or call a metered engine before the scan→select checkpoint and operator approval. |

Default inference: ordinary "research/look into" starts as `check` if it is a single question, `scan` if the request asks for options, and `dive` only when the user explicitly asks for deep paid research. State the inferred tier before acting: "I am treating this as `check`; say `--scan` or `--dive` to change it."

## Engine Override

| `--engine` | Tiers | Cost posture |
|---|---|---|
| `claude` | T0-T2 | Free on the operator's subscription path; announce planned search/tool budget. |
| `perplexity` | T1-T2 grounded lookup; T3 alternate only by request | Metered. Announce estimate before spending and actual after. Missing key is a config error. |
| `gemini` | T3 dive | Existing `deep-research` gate. Estimate before approval; do not bypass its redaction/cost checks. |

No engine auto-spends. If a metered key is missing, stop with a config error; never silently fall back to a different paid engine.

## T3 Dive Protocol

The `dive` tier is a four-step gate. Never compress it.

1. **Scan first (free).** Run T0-T2 recon to produce a ranked candidate shortlist. File nothing yet.
2. **Select.** Present candidates with one-line rationale each. Stop and wait for operator selection. Do not start the paid run until the selection is explicit.
3. **Estimate.** Read `references/engines.md`. Run `--dry-run` on the selected brief. Announce: engine, model, estimated cost, depth, stop condition. Do not spend before announcement.
4. **Dive.** Only after operator approval: run the deep-research adapter at `--depth quick` (default); `standard` or `deep` on explicit request. Pass the full brief packet. On completion: write `RUN_META.md`, run redaction audit (`grep -rE 'AIza[A-Za-z0-9_-]{35,}|GEMINI_DEEP_RESEARCH_API_KEY='` → must be 0 matches), file the synthesis to `context/research/<topic>/`, add an INDEX row, run `scripts/check-surface.sh`.

**T3 alternate (Perplexity `sonar-deep-research`):** same gate, same four steps. Requires `PERPLEXITY_API_KEY` in environment (config error if missing). Anchor-quote verification is **mandatory** on its output — every load-bearing claim must carry a `≤150`-char verbatim quote and pass a re-fetch check. Never optional.

**Engines reference:** load `references/engines.md` for request shape, cost ranges, and key-missing behavior before any paid run.

## Seven-Step Checklist

1. Route before researching: read `context/research/INDEX.md`. If an existing row covers the topic, revise that document in place and do not create a duplicate.
2. Interview before the run — **one batch, before any searching**. Ask the 3 unskippable questions in `references/interview.md`; add at most 3 more. Include pre-filled recommended answers. **Skip only when the request already answers all three** — a written brief, a task packet or a detailed prompt often does — and when you skip, **say so in one line naming what answered them**. A silent skip and a considered skip look identical to the operator, which is why the declaration is required, not optional. A dispatched worker running from a brief skips by default: a missing brief field is a stop condition, not a question to a human who is not there. Never interview once the run has started.
3. Pick tier and fan-out. One sub-question stays inline. 2-4 independent subtopics may use subagents. More than 4 means split the request or ask to raise the cap.
4. Brief each subagent with `references/subagent-brief.md`. Boundaries are the dedup layer: one path, touch nothing else, return a proposed index row.
5. Checkpoint every return immediately under `context/research/<topic>/.wip/`: `brief.md`, `returns/<agent>.md`, `sources.jsonl`, and `run-state.md`. A fresh session resumes from these files before doing new work.
6. Synthesize once from the saved returns, then verify citations by refetching anchor quotes. Delete contradicted claims; mark unresolved support `[U]`.
7. File to the body template, **delete the topic's `.wip/` directory**, regenerate the index with `bash scripts/build-index.sh context/research`, run `bash scripts/check-surface.sh context/research`, then report done. Both scripts ship with this skill; run them from the skill directory or by absolute path. Invariant I9 fails if any `.wip/` survives.

Backward edge: if citations are incomplete or contradictory, return to step 3 with a smaller question.

## Delegation Defaults

| Shape | Default | Rationale |
|---|---|---|
| One question, 3-10 fetches | Inline; delegation: none. | Subagents cost coordination and tokens without adding depth. |
| 2-4 independent subtopics | 2-4 subagents, about 15 tool calls each. | Boundaries stay understandable and fit the shared session search cap. |
| More than 4 subtopics | Split the request. | Fan-out multiplies cost and citation work; it is not a substitute for scope control. |

Before spawning, state the planned tool-call budget. Stop if the plan would exceed the configured session allowance.

## Filing Rules

- Preserve root `research.md`; the durable surface is `context/research/`.
- Keep one topic in one document when the index already has coverage.
- Write scaffolding only when needed: topic directory, `.wip/`, and the final document path.
- `.wip/` is scratch, never corpus. It holds raw pre-verification returns, so it must not outlive the run: delete it once the synthesis is filed. Never commit it. If a run dies mid-flight, `.wip/` is what the next session resumes from — deleting it is the *last* step, not an early one.
- Pointer writing: every final answer names the filed document and the index row used or updated.
- Scan outputs may be filed only as scan docs and must not reach a conclusion.
- Check and dive outputs must use `references/body-template.md`.
- Do not complete if `scripts/check-surface.sh` exits non-zero.

## Reference Loading

Load only the reference needed for the current step:

- `references/interview.md` before asking questions.
- `references/subagent-brief.md` before delegation.
- `references/body-template.md` before filing.
- `references/engines.md` before any `--engine perplexity` or `--engine gemini` path.
- `references/domain/*.md` for source priorities.
- `references/high-stakes.md` when the user requests high-stakes or policy-grade work.
- `references/prompt-patterns.md` when preparing a prompt packet.

## Eval Anchors

- Shallow lookup: use `check`, delegation: none, and cite sources or say unverifiable.
- Covered topic: route through `INDEX.md`; revise in place; no duplicate document.
- Unanswerable: say "nothing credible found" or "not enough credible evidence"; do not pad.
- Forced `--scan`: label scan-only, list open questions/next checks, and never conclude.
- `dive`: stop for approval with estimate and engine before spending.
- Read-side reuse: in a fresh session, use `INDEX.md` before new research.
- Produced surface: run `scripts/check-surface.sh`; `PASS` or stop.

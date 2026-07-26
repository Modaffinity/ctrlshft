# Engines

## Claude

Default for T0-T2 subscription work. Cost is $0 at the API boundary for the operator's subscription path, but search/tool calls are still scarce. Announce planned search budget before fan-out.

## Perplexity

Use only when the operator selects `--engine perplexity` or approves a metered route.

Models:

- `sonar`: grounded lookup for T1/T2. Cost: ~$0.005–0.01 per query.
- `sonar-pro`: higher quality grounded lookup for T1/T2. Cost: ~$0.05–0.10 per query.
- `sonar-deep-research`: T3 alternate only, behind the dive approval gate. Cost: ~$0.40–1+ per run (no official average; treat as variable). Anchor-quote verification is **mandatory** on its output — never optional.

Request shape for T1/T2 (`sonar` / `sonar-pro`):

```json
{
  "model": "sonar",
  "messages": [
    {"role": "system", "content": "Answer with citations and do not exceed the requested scope."},
    {"role": "user", "content": "<brief>"}
  ],
  "max_tokens": 800,
  "temperature": 0.2
}
```

Request shape for T3 (`sonar-deep-research`):

```json
{
  "model": "sonar-deep-research",
  "messages": [
    {"role": "system", "content": "You are a research assistant. Produce a structured report with citations. Every load-bearing claim must carry a verbatim quote of ≤150 chars from the cited source."},
    {"role": "user", "content": "<full brief packet>"}
  ],
  "max_tokens": 4000,
  "temperature": 0.1
}
```

Before spending, announce:

- selected model,
- estimated cost range,
- expected question count,
- stop condition,
- that actual cost will be reported afterward.

If `PERPLEXITY_API_KEY` is missing or empty, stop with: "Config error: PERPLEXITY_API_KEY is required for --engine perplexity." Never silently fall back.

## Gemini

**Availability: container only.** This path runs through the `deep-research` adapter at
`~/cortextos/skills/deep-research/`, which exists **only inside the CortexOS container**. On the host —
where `/research` runs — that directory does not exist and there is no host copy of `deep-research`, so
the pointer below is dangling there. A host `dive` has exactly two honest routes:

1. Use the **T3 alternate**: Perplexity `sonar-deep-research` (§Perplexity above), behind the same
   approval gate, with anchor-quote verification mandatory.
2. **Dispatch the dive to a container agent** that has the adapter.

Check which environment you are in before you promise a Gemini dive, and say which route you are taking.
Never announce a dive you cannot run.

Use only for T3 `dive`. Preserve its dry-run estimate, approval gate, and redaction audit.

Cost: $1–3 typical (`quick`); $3–7 (`standard`/`deep`). Dry-run estimate is a conservative ceiling-gate, not a spend forecast — observed actuals have been significantly lower.

**Protocol (container only): read `~/cortextos/skills/deep-research/SKILL.md`** — the proven
dry-run/approval gates, the non-blocking three-step invocation, and the completion contract
(`RUN_META.md`, redaction audit, commit) live there and are not restated here. That package is deployed
and catalog-visible but deliberately not linked to any agent: read it by path when you reach this tier.

**It is deployed as `SKILL.md` alone** — seven companion documents it references (its operating model,
artifact schema, readme, and its brief/packet/task templates) were **not deployed with it**. Do not go
looking for them and do not treat their absence as a blocker. What they would have supplied, you
already have: the four-step gate is in this skill's `SKILL.md` §T3 Dive Protocol, the cost calibration
is the band above, and the completion contract is — write `RUN_META.md` into the run folder, run the
redaction audit, file the synthesis to `context/research/<topic>/`, add the INDEX row, run
`scripts/check-surface.sh`. **If `deep-research/SKILL.md` asks you to consult a file that is not there,
proceed on the above rather than stopping.**

Prerequisite: `GEMINI_DEEP_RESEARCH_API_KEY` in environment. If missing, stop — do not retry.

**Known limitation — anchor-quote verification degrades on this path.** Gemini returns *grounding
redirect* URLs, not publisher URLs, so the `curl` + normalized-substring re-fetch cannot reach the
source page. First real dive (2026-07-25, `citation-verification`): **all 16 sources resolved `[R]`
(page supports, anchor missed), zero `[V]`.** That is the expected outcome here, not a failure to
investigate — but **do not report a Gemini dive as anchor-verified.** Mark T3 findings `[R]` unless
you independently resolved a publisher URL and matched the quote against it. The `[V]`-grade
verification the spec designs for is currently reachable on the T0–T2 paths only.

No OpenAI deep-research route is wired for this skill.

# Body Template

Use this exact structure for filed research documents. Replace bracketed text; delete comments before filing.

```markdown
---
topic: [slug]
tasks: [skill-build]
tags: [[domain], [topic]]
status: draft
updated: YYYY-MM-DD
last_verified: YYYY-MM-DD
sources:
  - [up to 12 routing sources]
summary: "[Conclusion-first summary, <=200 chars.]"
---

# [Subject]

**[Bold conclusion in 1-3 sentences.]** [Explain what this is, the answer, and why it matters inside the first 25 lines.]

Question: [Explicit question being answered.]

## Findings

| # | Claim | Source |
|---|---|---|
| F1 | [One load-bearing claim.] [V/R/U] [high/med/low] | [URL or citation plus anchor quote <=150 chars] |

## Detail

[Short headed sections with evidence and caveats. Keep one claim per row when comparing options.]

## What this implies

1. [Directive or decision, with back-reference to F1.]

## What was searched / excluded

| Query or source | Result | Kept/excluded and why |
|---|---|---|
| "[exact query]" | [candidate/source] | [reason] |

## Not verified / open

- [Unanswered item, failed source, or "None beyond stated caveats."]

## Changed since last revision

- [Only on revision: what moved and why.]

## Sources

- [Full source list if frontmatter was capped.]
```

## Body Checks

- `head -25` contains the H1 and bold conclusion.
- `sources:` has no more than 12 entries; overflow goes in `## Sources`.
- `What this implies`, `What was searched / excluded`, and `Not verified / open` are present unless explicitly inapplicable.
- Every load-bearing claim has provenance `[V]`, `[R]`, or `[U]` plus confidence `high`, `med`, or `low`.
- Contradicted claims are deleted.
- Scan docs do not conclude; check and dive docs reach exactly one answer.

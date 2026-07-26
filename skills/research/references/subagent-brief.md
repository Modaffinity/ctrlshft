# Subagent Brief

Use this only when delegation is justified by 2-4 independent subtopics.

```markdown
## Objective

[One sub-question this subagent owns.]

## Output format

- Findings table: one claim per row.
- Each load-bearing claim includes source URL, anchor quote <=150 chars, provenance mark candidate, and confidence.
- Include "nothing credible found" if sources fail rather than padding.

## Source guidance

- Prefer primary sources and registries for the domain.
- Record exact queries and considered-but-rejected candidates.
- Do not use another subagent's scope.

## Boundaries

- Write exactly this one return file: `context/research/<topic>/.wip/returns/<agent-or-scope>.md`.
- Touch nothing else.
- Return a proposed INDEX row; do not edit `INDEX.md`.
- Stop if a metered tool would be needed and no approval was granted.
```

On every return, copy the result to `.wip/returns/` before synthesis. The checkpoint is the recovery point if the session dies.

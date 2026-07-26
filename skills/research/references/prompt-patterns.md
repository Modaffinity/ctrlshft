# Prompt Patterns

Use these SEG-labeled sections when preparing briefs or engine-specific prompt packets.

## SEG-ROLE

State the role and domain first: "You are researching [domain] for [decision]."

## SEG-TASK

Put the exact question last in the setup block so it remains salient.

## SEG-CONTEXT

List scope boundaries, disqualified sources, and what would change the answer.

## SEG-OUTPUT

Demand tables for findings, one claim per row, source inline, and anchor quotes <=150 chars.

## SEG-CONSTRAINTS

Move engine controls into API parameters when the provider supports them. Do not encode token or section caps only in prose.

## SEG-VERIFY

Require a separate citation check pass. The final answer may not be stronger than the source it cites.

## SEG-FILE

For durable runs, name the exact final path and the `.wip/` checkpoint paths.

# Routing table

Resolves a goal's declared requirements to an owning specialist and a `spawn-worker --model`.
Used by the operator at dispatch time — **this is a lookup table, not a routing layer.**

**Source:** operating model §2 routing matrix (role ownership is doctrine-fixed).
Model pins: live agent configs, read 2026-07-27. The documented defaults in the pod execution
model (`claude-opus-4-8`) predate the current roster — **no agent runs that pin.**

---

## How to use

1. Read the goal's direction and kind of work.
2. Find the matching requirement below.
3. The **owning specialist** is the `--assignee` on the bus task.
4. The **worker model** is the `--model` on `spawn-worker`.

If the goal's requirements span two rows with different owners, it is **two goals** — ownership
beats size (SPEC §4a factor 3). If no row matches, **stop and escalate to the operator** — do not
invent an assignment.

---

## The table

| Requirement | Owning specialist | Worker model | Why |
|---|---|---|---|
| Web search · free recon · source evaluation · evidence packages · source tables · citations | research-agent | `claude-sonnet-4-6` | Research capability is exclusive to research-agent (sole key). Sonnet: standard structured research |
| Paid research · Deep Research · paid Gemini · research-cost capture | research-agent | `claude-opus-4-6` | Paid calls are research-agent exclusive. Opus: judgment-heavy paid work justifies the stronger model |
| AIM strategy · framing · acceptance criteria | aim-agent | `claude-sonnet-4-6` | AIM domain ownership per routing matrix. Sonnet: standard framing and criteria work |
| AIM domain quality judgment · enrichment synthesis | aim-agent | `claude-opus-4-6` | High-judgment AIM assessment. Opus: quality judgment needs the stronger model |
| Independent review · critique (verdict-first) | codex-review-agent | `gpt-5.5` | Codex runtime (not `spawn-worker`); on-demand protocol per `codex_on_demand_review.md`. Triggered and bounded (≤3 rounds) |
| Structured implementation · build · document production | ephemeral worker | `claude-sonnet-4-6` | No named specialist owns general build work. `--parent` = the specialist who dispatched. Sonnet: standard structured tasks |
| High-judgment synthesis · complex analysis · multi-source integration | ephemeral worker | `claude-opus-4-6` | Same as above but the work requires deeper judgment. Opus: complex reasoning justifies the cost |
| Coordination · routing · status · envelope enforcement | orchestrator-agent | — (standing) | Standing agent; does not execute specialist work. No worker: the orchestrator routes, it does not produce deliverables |

---

## Notes

The **judge** kind (gate 2) resolves via the *Independent review · critique* row
(`codex-review-agent`), which also satisfies SPEC §5's different-model-from-producer
requirement whenever the producer is a Claude worker.

- **Research is exclusive.** No row assigns research or paid work to any agent other than
  research-agent. This is doctrine (operating model §2, §3 capability ownership).
- **codex-review-agent runs on `codex-app-server`**, not `claude-code`. It is not spawned via
  `spawn-worker`; it is started and stopped via the on-demand review protocol. Its `enabled: false`
  state is correct when no review is active.
- **Ephemeral workers need a `--parent`.** The parent is the owning specialist who dispatched the
  goal. The worker inherits no standing memory.
- **Always pass `--model` explicitly.** Omitting it can trigger a "model not available" loop
  (upstream issue #345).
- **opus-agent and gpt5-agent** are in the live roster but do not appear in the routing matrix.
  They are not listed here because the table may not invent role ownership.

## Model pin source (2026-07-27)

| Agent | Config model | Runtime |
|---|---|---|
| orchestrator-agent | `claude-sonnet-4-6` | claude-code |
| research-agent | `claude-sonnet-4-6` | claude-code |
| aim-agent | `claude-sonnet-4-6` | claude-code |
| opus-agent | `claude-opus-4-6` | claude-code |
| codex-review-agent | `gpt-5.5` | codex-app-server |
| gpt5-agent | `gpt-5.5` | codex-app-server |

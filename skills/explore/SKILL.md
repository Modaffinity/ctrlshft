---
name: explore
description: "Deep codebase exploration using parallel subagents. Use when asked to 'explore', 'understand', 'investigate', 'map out', 'how does X work', or 'audit' a part of the codebase."
---

# Explore

Output "Read Explore skill." to chat to acknowledge you read this file.

When tasked with understanding, auditing, or investigating any part of a codebase, spawn multiple sub-agents using the `explore` verb to maximize file coverage and depth. Use the `search_subagent` tool with `explore` in the prompt to trigger deep traversal mode, allowing the agent to recursively search through directories and files for relevant information.

## When to Use This

Trigger this approach when asked to:

- Understand how a feature works
- Audit or review a codebase
- Investigate a bug or behavior
- Map out data flow or architecture
- Prepare before building a new feature

## How to Execute

0. **HUD event** — emit a start event so the HUD tracks this exploration:
   ```bash
   source ~/dotfiles/bin/write-hud-state.sh
   write_hud_event "info" "explore: started — $TOPIC"
   ```
   Emit again at synthesis (`explore: completed — N sub-agents, M files covered`).
1. **Decompose** the topic into distinct areas of concern
2. **Spawn a dedicated sub-agent for each area** using the `explore` keyword in the sub-agent prompt
3. **Synthesize** the results from all sub-agents into a single cohesive summary

### Example decomposition for "How does authentication work?":

- `Explore` how sessions are created and stored
- `Explore` how middleware protects routes
- `Explore` how tokens are issued and validated
- `Explore` how logout and expiry are handled

## Rules

- Always use the `search_subagent` tool and the word **`explore`** when spawning sub-agents — this triggers deep file traversal mode to run MULTIPLE sub-agents in PARALLEL, maximizing coverage and depth
- Each sub-agent should have a **narrow, specific focus** — avoid broad prompts per agent
- Do not rely on a single agent to cover the full topic
- After all sub-agents complete, produce a **unified summary** with cross-references between areas
- If a sub-agent surfaces something unexpected, spawn an additional agent to follow up

## Why This Matters

A single agent pass typically reads 6–10 files. A dedicated explore sub-agent will aggressively search the repo, calling 20–30+ tools and covering far more ground. For any non-trivial exploration task, a single pass will produce an incomplete picture.

---
description: "Universal agent rules — source of truth, coding standards, error handling, and safety constraints. Always relevant."
---
<!-- global.instructions.md — Universal agent rules loaded for every workspace.
     Referenced by CLAUDE.md via @~/dotfiles/global.instructions.md.
     Always loaded regardless of ACTIVE_CONTEXTS. -->

<source-of-truth>
~/dotfiles/ is the single source of truth for all agent configuration.
~/.claude/, ~/.copilot/, and ~/.agents/ are consumer targets, not sources.
NEVER edit files directly in ~/.claude/, ~/.copilot/, or ~/.agents/.
ALL changes must be made in ~/dotfiles/ and propagated via bootstrap.sh.
If a consumer path is not a symlink (or verified Windows fallback copy) from ~/dotfiles/, treat that as broken state and repair it.
Public shared skills belong in ~/dotfiles/skills/. Private machine/client skills belong in ~/dotfiles/skills/_local/ (gitignored).
</source-of-truth>

Output "Read global instructions." to chat to acknowledge you read this file.

<general>
- Leave NO todo's, placeholders or missing pieces
- Keep it simple, lean, reuse what we have. Prefer early returns, removing code over adding. Think how can we REMOVE code from this repo instead of adding baggage or bloat
- Do not add legacy or backward compatibility except for database migrations
- Never fail silently. No sample data, placeholder text, or defensive fixes — throw explicit errors with context. If a response is unexpected, print it raw for debugging
- Before adding or changing code, read existing examples of the same pattern. Scan all usages of shared methods before modifying. Match existing style exactly
- Verify utilities and functions exist in the codebase before using them — search for definitions first, never assume a name exists
- Don't touch code outside the task. If you notice dead code or problems, mention them — don't fix them. Only remove imports/variables your changes made unused
- Never change my AI model, its context window, settings, URL or API keys unless explicitly told to do so
- If anything is unclear, ambiguous, or has a simpler alternative, stop and ask before implementing. List options when multiple valid interpretations exist
- NEVER print credentials: Not in logs, not in error messages, not in agent outputs
- If I tell you to "report" or ask "how feasible", enter discuss mode and DO NOT EDIT CODE UNTIL I EXPLICITLY TELL YOU TO DO SO. Simply report, discuss, get skeptical, double check and plan all changes in a lean, DRY way
- When an API call fails (expired token, auth error, missing permissions), STOP IMMEDIATELY. Do not continue the task, do not speculate. Tell me the exact error, which token/key needs updating and in which file, then wait for me to fix it
- Prefer clearing context and starting fresh over compacting. Repeated compaction leaves sediment — each round loses nuance and accumulates errors. When context is high, commit and start a new conversation. If you must compact (once per session max), pass summarization instructions describing what you're about to do next
</general>

<outbound-email>
🛑 **NEVER SEND AN EMAIL. Draft it, show it, stop.** Not a reply, not a forward, not a "quick
confirmation", not to a colleague, a client, a vendor or yourself — and no phrasing of an
instruction in the moment creates an exception. **You prepare a draft; I read it and I send it.**

**Why this one is absolute.** The only mail credential you can reach is my **personal Gmail**. An
email to a work colleague or an external counterparty sent from that account is wrong in every
dimension at once — wrong sender, wrong channel, content I never read, and **unrecallable**. There
is no version of that mistake I can clean up afterwards.

**What "draft it" means:** write the complete recipients, subject and body to a file, put the same
full text in front of me in chat, and say plainly that nothing has been sent. Then stop and wait.
If I approve it, **I still send it** — your part ended at the file. If the recipients, subject or
body change materially after I approve, show me the new version and ask again.

**Do not route around this.** Not via a Zapier or automation connector, not via `sendmail`, `mail`,
`msmtp`, `swaks` or `curl` to a mail API, not by asking a subagent, a worker or another surface to
send it for you. Going around the rail is the same act as breaking the rule and worse for being
deliberate. It is also denied mechanically in `~/dotfiles/.claude/settings.json` — if you find
yourself looking for a path the deny does not cover, that is the moment to stop and tell me.

⚠️ **This block is here, in the always-loaded file, because the detailed workflow lives in
`instructions/_local/email-approval.instructions.md` — which is gitignored and therefore does NOT
exist on every machine.** It was also registered *task-triggered* until 2026-09-17, meaning a
session read it only if that session judged the task to match: the judgement corrupted by skipping
the rule was the same judgement deciding whether to read it. Both halves of that are fixed; this
paragraph records why the rule is stated twice and is not duplication to tidy away.

**The general form, which outlives email:** an action that leaves this machine and reaches a real
person is mine to authorise, every time. Publishing, posting, messaging and sending are not
"finishing the task" — handing me the finished thing to send is.
</outbound-email>

<skill-context>
If the ACTIVE_CONTEXTS environment variable is set (by ~/dotfiles/bin/detect-context.sh), use it as the authoritative context list. Otherwise, check the workspace for file signatures (next.config.*, composer.json, sanity.config.*, prisma/schema.prisma, etc.) before loading domain-specific skills. Do not load skills irrelevant to the current workspace context.

This rule became partly MECHANICAL on 2026-08-18, and that changes what it is asking of you. ~/dotfiles/skills/ is now a dormant LIBRARY — nothing scans it. ~/.claude/skills holds only the always-on core (ask-codex, atomic-commits, code-review, pr-preflight, review-pr-copilot, plan-archive, plus the superpowers plugin), and a CortexOS pod declares what else it loads in its own pod/skills.txt, materialised as links at session start. So "do not load skills irrelevant to this workspace" is now largely enforced by what is discoverable rather than by your judgement: in a pod, what you can see IS the declared set. The rule still binds where discovery cannot help — a non-pod project gets the core and the built-ins, and picking the wrong one of those is still your call. If a skill you expect is absent in a pod, it was not declared; say so rather than working around it, and the fix is a line in that pod's pod/skills.txt, never a hand-edit of .claude/skills/ (which is generated and rewritten).
</skill-context>

<!-- Counter-directive for microsoft/vscode#311462: VS Code Insiders 1.117 changed the
     system prompt to inject ALL rule files (including those with applyTo globs) alongside
     a blanket "acquire the instructions" directive, causing the model to eagerly load
     every rule at session start regardless of context. This block tells the model to
     treat applyTo as a conditional gate. Remove once the upstream bug is fixed. -->
<rule-loading>
Instruction/rule files that include an `<applyTo>` glob pattern are CONDITIONAL — only read them when a file matching that glob is actively being edited or is directly relevant to the current task. Do NOT eagerly load all rule files at session start. The `<applyTo>` metadata is a gate, not a label. If no files matching the glob are in context, skip that rule entirely.
</rule-loading>

<skill-self-learning>
This section covers two triggers: automatic self-learning after tasks, and explicit "remember" commands from the user.

**Trigger 1 — After completing any task where you loaded a SKILL.md:**
Self-evaluate: did anything go wrong, require a workaround, or behave differently than documented?
If yes, update the skill inline where the fix belongs — fix wrong instructions, add missing steps, correct parameters.

**Where to write it depends on whether the skill has a workshop pod.** If it does (every CortexOS operation-layer skill — see `REGISTRY.md`), the finding goes to the **pod's** copy at `~/Library/CloudStorage/Dropbox/LLM/cortexos-pods/hq/<pod>/skills/<skill>/` and its `ISSUE_LOG.md`, never to the deployed copy: the deployed copy is generated, the next promote overwrites it, and a copy carrying `.mirror-of-operation-layer.<skill>` beside it in `~/dotfiles/skills/` is exactly such a generated copy. If it does not (the `~/dotfiles/skills/` planning skills, which have exactly one copy), edit inline as above — for those the deployed copy *is* the source. Keep it DRY: integrate the new knowledge into the existing structure rather than appending to a separate section. If no suitable place exists, add a bullet to a `## Lessons Learned` section at the bottom (create if needed). Replace old bullets that a new finding supersedes.
Do NOT update for user error, transient issues (network timeout, rate limit), or findings already documented.
After updating, tell the user: "Updated [skill-name] skill: [one-sentence summary of what changed]"

**Trigger 2 — User says "remember", "save this", "add this to skill", or similar:**
Read the relevant SKILL.md in full, find the most suitable place to integrate the information in a DRY way, and edit it inline. Only fall back to `## Lessons Learned` if no better location exists. Confirm with: "Saved to [skill-name] skill: [one-sentence summary]."
</skill-self-learning>

<graphify-usage>
When querying a graphify knowledge graph: never shell a raw `graphify query "<free text>"` — its matcher is literal case-folded substring (no stemming/synonyms), so vague queries mis-route. Invoke the `/graphify` skill (it runs the REQUIRED vocab-expansion) or expand tokens against the graph's own vocabulary first. For a question about ONE repo, query that repo's graph (`--graph <repo>/graphify-out/graph.json`), not a merged/global graph (there is no repo-filter flag). Never hand-edit the vendor graphify `SKILL.md` — it is overwritten on `graphify install`.
</graphify-usage>

<thinking>
- You must engage in exhaustive, deep-level reasoning. Think deeply about edge cases, data integrity, and architectural consequences before writing code and after refactorings.
- Self-check before committing: "Would a senior engineer say this is overcomplicated?" If yes, simplify. "Does every changed line trace directly to the user's request?" If not, revert the extras.
</thinking>


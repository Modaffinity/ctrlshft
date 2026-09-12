---
name: ask-codex
description: "Ask OpenAI Codex — a second model with a different training lineage — for a review, a second opinion, or a verdict on whether a suite passes. Use when asked to 'ask Codex', 'get a second opinion', 'have another model check this', 'does this look right', 'sanity-check this change', or before merging something you cannot easily verify yourself. Also use when deciding between the fenced ask-codex command and the raw MCP codex tool."
---

# ask-codex

Output "Read ask-codex skill." to chat to acknowledge you read this file.

**`ask-codex` is the fenced way to reach Codex. The `mcp__codex__codex` tool is the unfenced way.**
Both work, they are not interchangeable, and the difference is not politeness — see §"Which path".

## One command

```bash
ask-codex -- 'is the locking correct?'                        # the change, as a diff
ask-codex src/auth.ts docs/ -- 'do these contradict each other?'   # copies of those paths
```

Name paths and Codex gets copies of exactly those; name none and it gets the uncommitted change as
text. Either way it stands in an otherwise empty directory and the repository is never readable.
**You do not pick a fence and cannot widen one** — both forms run the same read-only profile, network
and web search off, `~/**` denied. Your input selects only what Codex is *shown*.

It refuses rather than guesses: a path that does not exist (it would otherwise be read as part of
your question), and paths together with `--base`/`--commit`/`--uncommitted` (documents and a diff are
two different requests). Each refusal names the alternative.

Every run files `evidence/codex-<mode>-<stamp>/` in the current repo — the report, the exact
invocation, the raw event stream, and what the model actually executed.

## The two words you still type

Inference never selects these. A wider fence is asked for by name.

| | What Codex sees | Why it stays explicit |
|---|---|---|
| **`ask-codex review [--base <ref>]`** | the whole working tree | it reads everything, *including review documents lying in it* |
| **`ask-codex gate ['instructions']`** | a disposable clone it may write to | the one mode that writes; returns a PASS/FAIL verdict |

⚠️ **`review` has a known contamination mode** — Codex has reported a defect it read in a previous
`review-*.md` as though it had found it. Do not use it to measure review quality, count findings, or
ask whether something is *novel*. Use it when the change is small but its context is not: a one-line
edit whose correctness depends on a caller elsewhere, a rename whose blast radius is the point.

`ask-codex blind …` and `ask-codex scoped …` still work — 44 references across four other pods
depend on them — but you need not type them: `scoped` is what naming paths does, `blind` what naming
none does. `blind` is also the *profile* both inferred forms use, which is why a report says
`profile_used: blind` even when you named paths.

## What the fence actually is

Policy lives in `~/.codex-agent/*.config.toml`, deployed from `~/dotfiles/codex/`, so widening it is
a committed diff rather than a flag someone typed. There is no sandbox option on the command line and
never will be, and the wrapper refuses to run on a loosened policy.

**Containment is by placement, not by permission rules.** Codex's permission model subtracts rather
than scopes — every "only this" must be written as "not those", which fails open on whatever nobody
enumerated. So the fences work by standing in an empty directory holding only what they should see.
Nothing is granted, so nothing can be got wrong.

Four refusals, each chosen over a best effort:

- **An oversized diff is not truncated.** A shortened diff reviews a change you do not have, in the
  same voice as any other. It refuses and names the largest files.
- **A path resolving outside the repo is not copied**, symlinks included. A symlinked file inside the
  repo arrives at **the path you named** carrying the target's bytes; a symlinked *directory* is
  refused by name, and excluded directories (`.git`, `node_modules`, `__pycache__`, `.codex`) are
  reported rather than dropped quietly.
- **A `gate` verdict its own event stream does not support is rejected.** A repository can tell Codex
  what to report, so the wrapper cross-checks the claimed suite against the commands that ran.
- **Host skills are not advertised to it.** A 43-entry catalog of paths this fence denies reached
  every run until 2026-09-11; Codex announced skills it then could not open. Off in every profile.

## Which path — and why this matters more than it looks

**`ask-codex` is enforced. The MCP `codex` tool is not.**

**Enforced literally, not as a manner of speaking.** A permission rule denies
`/Applications/ChatGPT.app/Contents/Resources/codex` — the absolute path, because `codex` is not on
`PATH` and a rule naming it would deny a string nobody can execute — along with both
`--dangerously-bypass-*` flags. `ask-codex` is allowed outright and needs no approval. If you reach
for bare Codex the shell refuses you; that is working as intended.

The MCP tool is genuinely better for free-form back-and-forth: `codex-reply` gives real multi-turn
argument, and `ask-codex` gives you one shot. Use it for thinking out loud with another model.

🛑 **But it takes a `config` argument reaching `sandbox_mode` directly, and no permission rule can
bind it** — rules match strings and `config` is an object. It is *defaulted* to read-only through the
agent `CODEX_HOME`, and that default is not enforced: a prompt, a repo, or a mistake can widen it.

**So anything that must be contained goes through `ask-codex`** — reviewing code you did not write,
touching a repository you do not trust, running a suite. "What do you think of this approach" is fine
over MCP.

This is stated at the point where you pick, rather than in a document you would have to go looking
for. It is the only control there is: nothing stops the MCP path, so the defence is that you were not
misled about which path is which.

### 🛑 If `ask-codex` will not run, STOP. Do not substitute the MCP tool.

**Measured, on the first session ever given this skill.** Asked to have another model inspect an
untrusted repository *without anything in it executing*, a fresh session correctly chose the fenced
path. The command came back **"This command requires approval."** The session then called
`mcp__codex__codex` directly — the unfenced path — for the task whose whole premise was containment.
Nothing went wrong with its reasoning. It wanted to finish, the fenced door was shut, and an open
door was right there.

*That trigger is closed; `ask-codex` no longer prompts. The rule is not, because an approval prompt
was only one way the door can shut — a missing profile, a failed `bootstrap.sh`, an expired login and
a harness sandbox all produce the same situation and the same temptation.*

**So: a blocked, missing or failing `ask-codex` is a stopping condition, not a routing decision.**
Report what happened and what it needs. Falling back to MCP converts a permission prompt into a
silent loss of containment, and whoever asked for containment will never know they did not get it.

The one exception is where containment was never the point: free-form thinking-out-loud, no untrusted
repository, nothing to contain. Then MCP was always right and this does not apply.

**There is no table of known failures here any more.** The wrapper names its own cause and remedy as
it refuses — including the harness-sandbox case, which it now detects *before* copying anything in
rather than after. Read what it says and do that.

## Reading what comes back

**Judge the artifact, never the exit code** — Codex returns **exit 0 on a refused write**. The
wrapper's own code is a real verdict (`0` completed, `1` gate FAIL, `2` suite never ran, `3` usage,
`4` environment or fence pre-flight failed, `5` nothing trustworthy was left); Codex's is not, and the
wrapper never passes it through.

A report's frontmatter states its reach, and it is authoritative in **both** directions — whether the
model claims *more* reach than it had or *less*:

- A finding naming a file outside what the report says was visible is a guess. Read it as one.
- ⚠️ **Codex also reports files it WAS given as missing.** Measured 2026-08-19: a report declined the
  whole task, marking all 34 items UNRESOLVED as *"Underlying transcript and summary are absent"*,
  while its own `scoped-manifest.txt` named every file and the frontmatter read `files_copied: 12,
  bytes_copied: 322856`. The delivery was fine; the model's account of its own reach was not. **Check
  the manifest before believing a claim of missing input** — it is the wrapper's record, not the
  model's. Re-running with the paths asserted in the prompt returned a full, correct adjudication.

## Every invocation leaves one line

`~/.local/state/ask-codex/runs.jsonl` gets one JSON line per invocation, including the ones that never
reached Codex — those are most of the interesting ones. Fence, inferred or named, profile, counts,
duration, a stable cause token, the evidence directory, the Codex CLI version. No prompt text, no file
names; repository paths *are* in it. Nothing to maintain: it exists so "how often does this fail, and
how?" has an answer that is not archaeology.

## Cost

Every call spends ChatGPT quota, `gate` most because it runs a suite. A note, not a gate: this costs
only when invoked. Do not let it stop you asking — a two-minute review that catches a real defect is
cheap, and that is the whole point of the tool.

---
name: ask-codex
description: "Ask OpenAI Codex — a second model with a different training lineage — for a review, a second opinion, or a verdict on whether a suite passes. Use when asked to 'ask Codex', 'get a second opinion', 'have another model check this', 'does this look right', 'sanity-check this change', or before merging something you cannot easily verify yourself. Also use when deciding between the fenced ask-codex command and the raw MCP codex tool."
---

# ask-codex

Output "Read ask-codex skill." to chat to acknowledge you read this file.

**`ask-codex` is the fenced way to reach Codex. The `mcp__codex__codex` tool is the unfenced way.**
Both work. They are not interchangeable, and the difference is not politeness — see
§"Which path" before choosing.

**Default to `blind`.** It is the mode that answers the common question ("is this change any good?")
while being unable to read anything except the change itself.

## The four modes

| | What Codex sees | Use it for |
|---|---|---|
| **`blind`** | the diff, as text, in an empty directory | reviewing a change — the default |
| **`scoped`** | copies of the paths you name, nothing else | "read these docs", "look at this package" |
| **`review`** | the whole working tree | when a finding needs a file the diff does not contain |
| **`gate`** | a disposable clone it may write to | running the suite and getting a PASS/FAIL verdict |

```bash
ask-codex blind                             # uncommitted changes
ask-codex blind --commit <sha> 'is the locking correct?'
ask-codex scoped docs/ src/auth.ts -- 'do these contradict each other?'
ask-codex review --base main
ask-codex gate 'run the suite and report'
```

Every run files `evidence/codex-<mode>-<stamp>/` in the current repo — the report, the exact
invocation, the raw event stream, and what the model actually executed.

### Picking between `blind` and `review`

**`blind` cannot follow a call site out of the diff.** That is the whole trade. If a finding would
need the file three directories away, `blind` will say so rather than guess — which is the correct
answer, not a failure.

Reach for **`review`** when the change is small but its context is not: a one-line edit whose
correctness depends on a caller elsewhere, a rename whose blast radius is the point.

⚠️ **`review` reads everything in the tree, including its own `AGENTS.md` and any review documents
lying around.** Codex has been observed reporting a defect it read in a previous `review-*.md` as
though it had found it. If you are measuring review quality, or counting findings, or want to know
whether something is *novel*, use `blind` — on a tree carrying prior review material, `review` cannot
tell you that.

## Which path — and why this matters more than it looks

**`ask-codex` is enforced. The MCP `codex` tool is not.**

**Enforced literally, not as a manner of speaking.** A permission rule denies
`/Applications/ChatGPT.app/Contents/Resources/codex` — the absolute path, because `codex` is not on
`PATH` and a rule naming it would deny a string nobody can execute — along with both
`--dangerously-bypass-*` flags. `ask-codex` is allowed outright, so it needs no approval. If you find
yourself reaching for bare Codex, the shell will refuse you; that is working as intended, and the
answer is a mode above, not a way around it.

The MCP tool is genuinely better for free-form back-and-forth: `codex-reply` gives real multi-turn
argument, and `ask-codex` gives you one shot. Use it for thinking out loud with another model.

🛑 **But it takes a `config` argument that reaches `sandbox_mode` directly, and no permission rule
can bind it** — rules match strings, and `config` is an object. It is *defaulted* to read-only
through the agent `CODEX_HOME`, and that default is not enforced. A prompt, a repo, or a mistake can
widen it.

**So: anything that must be contained goes through `ask-codex`.** Reviewing code you did not write,
touching a repository you do not trust, running a suite — those are `ask-codex`. "What do you think
of this approach" is fine over MCP.

This is stated here, at the point where you pick, rather than in a document you would have to go
looking for. It is the only control there is: nothing stops the MCP path, so the defence is that you
were not misled about which path is which.

### 🛑 If `ask-codex` will not run, STOP. Do not substitute the MCP tool.

**Measured, on the first session ever given this skill.** Asked to have another model inspect an
untrusted repository *without anything in it executing*, a fresh session correctly chose
`ask-codex scoped`. The command came back **"This command requires approval."** The session then
called `mcp__codex__codex` directly — the unfenced path — for the task whose entire premise was
containment.

*That particular trigger is now closed — `ask-codex` is allowed outright and no longer prompts. The
rule below is not, because the approval prompt was only one way the fenced door can be shut: a
missing profile, a failed `bootstrap.sh`, an expired login and a harness sandbox all produce the same
situation and the same temptation.*

Nothing went wrong with its reasoning. It wanted to complete the task, the fenced door was shut, and
an open door was right there.

**So the rule is explicit: a blocked, missing or failing `ask-codex` is a stopping condition, not a
routing decision.** Report what happened and what it needs — an approval, a `bootstrap.sh` run, a
`codex login`. Falling back to MCP converts a permission prompt into a silent loss of containment,
and the person who asked for containment will never know they did not get it.

The one exception is the one where containment was never the point: free-form thinking-out-loud, no
untrusted repository, nothing to contain. Then MCP was always the right tool and this does not apply.

### Known refusals and their remedies

Neither of these is a reason to fall back to MCP — both end with `ask-codex` running.

- **Exit 5 · empty event stream · stderr `failed to initialize in-process app-server client:
  Operation not permitted`** — the calling harness's command sandbox denied codex its own
  `CODEX_HOME`/PATH-alias writes; the fenced run never started. Re-run the same command with the
  harness sandbox bypassed: the wrapper's own policy files are the fence, so nothing is lost.
  (Observed under Claude Code's bash sandbox, 2026-08-10.)

  ⚡ **Under Claude Code, bypass the harness sandbox on the FIRST call — do not wait for the failure.**
  This entry existed and was read in full, and the run was still made sandboxed and still cost a
  round-trip (recurred 2026-08-11). A remedy written only as *what to do after it breaks* gets applied
  after it breaks. **There is nothing to weigh here:** the harness sandbox protects the calling repo,
  which `scoped`/`blind` never touch, so bypassing it removes no protection that was doing work — the
  fence is `~/.codex-agent/*.config.toml` and an empty working directory, neither of which the harness
  sandbox contributes to. On a large fence the wasted call is not free: it copies every byte in before
  failing.
- **Exit 4 naming `branch.*.vscode-merge-base`** — VS Code's merge editor writes that git config
  key routinely, so this recurs on VS Code-managed repos. Run
  `git config --unset-all branch.<name>.vscode-merge-base`, then retry; VS Code recreates the
  key harmlessly when it next needs it.

## What the fence actually is

The wrapper takes a **mode, never a sandbox**. Policy lives in `~/.codex-agent/*.config.toml`,
deployed from `~/dotfiles/codex/`, so widening it is a committed diff rather than a flag someone
typed. It refuses to run if that policy has been loosened.

**Containment is by placement, not by permission rules.** Codex's permission model subtracts rather
than scopes — every "only this" has to be written as "not those", which fails open on whatever nobody
enumerated. So `blind` and `scoped` work by standing in an empty directory holding only what they
should see. There is nothing to grant, so there is nothing to get wrong.

Three things it will not do, and each is a refusal rather than a best effort:

- **Truncate an oversized diff.** A shortened diff is a review of a change you do not have, delivered
  in the same voice as any other. It refuses and names the largest files.
- **Copy a path that resolves outside the repository**, including through a symlink. A symlinked file
  inside the repo arrives at **the path you named**, carrying the target's bytes; a symlinked
  *directory* is refused by name rather than silently skipped, and any excluded directory
  (`.git`, `node_modules`, `__pycache__`, `.codex`) is reported to you rather than dropped quietly.
- **Report a `gate` verdict its own event stream does not support.** A repository can tell Codex what
  to report; the wrapper cross-checks the claimed suite against the commands that actually ran.

## Reading what comes back

**Judge the artifact, never the exit code** — Codex returns **exit 0 on a refused write**. The
wrapper's own exit code is a real verdict (`0` completed, `1` gate FAIL, `2` suite never ran, `5` the
run left nothing trustworthy); Codex's is not, and the wrapper never passes it through.

A `blind` or `scoped` report's frontmatter states its reach. If a finding names a file outside what
the report says the model could see, it is a guess — the frontmatter says so explicitly, and it is
worth taking literally.

⚠️ **The reverse also happens: Codex can report that files it WAS given are missing.** Measured
2026-08-19 on a `scoped` run — the report declined the whole task, marking all 34 items UNRESOLVED
with *"Underlying transcript and summary are absent"*, while its own `scoped-manifest.txt` listed
every one of those files by name and the frontmatter read `files_copied: 12, bytes_copied: 322856`.
The delivery was fine; the model's account of its own reach was not. **So check the manifest before
believing a claim of missing input** — it is the wrapper's record, not the model's, and the two can
disagree. Re-running with the paths asserted in the prompt ("the transcripts ARE present in
./path/, list that directory and read them") returned a full, correct adjudication.

This is the same rule as the line above, pointing the other way: the frontmatter is authoritative
about what Codex could see, whether the model claims *more* reach than it had or *less*.

## Cost

Every call spends ChatGPT quota, and `gate` spends the most because it runs a suite. It is a note,
not a gate: this costs only when invoked. Do not let it stop you using `blind` — a two-minute review
that catches a real defect is cheap, and this is the tool's whole point.

# Interfaces

The seven templates the spine's stages exchange, copied here from `SPEC.md` character-for-character.
A template is copied, never paraphrased or summarised, by any stage or session that uses it.

## Output kinds

| Stage | Output kind | The return's OUTPUT block carries | May the subagent commit? | What the orchestrator verifies on disk |
|---|---|---|---|---|
| B1, B2, B4 | `file` | `ARTIFACT: <path>` and `LINES: <n>` | no | **before** the orchestrator's own commit: the file exists and its line count matches `LINES`. **After**: `git ls-files` shows it tracked |
| B3, B5 | `findings` | `ARTIFACT: none`, `ROUND: <n> of 3`, and the findings list | no | nothing on disk — the orchestrator writes the ledger block itself from the return |
| B6 | `commits` | `BRANCH: <repo>: <name>` (one line per repo when the workstream spans two), `COMMITS: <repo>: <first>^..<last>` (one line per repo; see `STATE.md`'s `**Commits:**` field below for the root-commit case), `TASKS: <done> of <total>` | **yes** — one commit per task, `git add` by named path only | `git log --oneline <first>^..<last>` lists one commit per plan task, per repo; the branch head is `<last>` |
| B7 | `files` | `ARTIFACT: plans/<slug>/DOCS.md`, `LINES: <n>`, `ALSO CHANGED:` one path per line | no | **before**: `DOCS.md` exists and its line count matches `LINES`, and every `ALSO CHANGED` path appears in `git status --porcelain`. **After**: `git ls-files` shows `DOCS.md` tracked |
| B8 | `merge` | `MERGE: <repo>: <sha>` (one line per repo when the workstream spans two), or `ARTIFACT: none` with `VERDICT: stop` | **yes** — the merge commit only | `git rev-parse <sha>^2` resolves to the workstream branch tip, per repo; `git status --porcelain` is empty |
| B9 | `move` | `MOVED: plans/<slug> -> plans/archive/<slug>` — the **intended** target, not yet performed — and the report text | no — see [Land, and the archive](BUILD_SESSION.md#land-and-the-archive): the orchestrator, not this subagent, performs and commits the `git mv` and the `plans/INDEX.md` move, after `STATE.md`'s ledger commit | **before**: nothing beyond the report text being present. **After** the orchestrator's own `git mv` (a later, separate step): the new path exists, the old does not, and the `plans/INDEX.md` row moved |

A stage may write, commit or move **only** what its kind permits. There is no kind that permits
writing `STATE.md`: that file is single-writer and the orchestrator owns it.

## The dispatch brief

A recipe, not a prohibition list, because the failure it prevents is wrong-shaped output rather
than a broken rule (superpowers `writing-skills`, *Match the Form to the Failure*).

```markdown
You are the **<stage name> stage** of a build session for the workstream `<slug>`.
Claude decides, Codex advises; do not be timid and do not be reckless.

**Working directory:** <absolute pod path>. Branch `<branch>`. Do not change branch.

**Your deliverable:** <the OUTPUT block's contents for this stage's kind, spelled out>.
Write nothing else.

**Commits:** <one of — "Do not commit; the orchestrator commits." | "Commit once per task,
`git add` by named path only, never `git add -A`." | "The merge commit is yours; nothing else."> The
B9 stage always gets the first form: the `git mv` and `plans/INDEX.md` move are the orchestrator's,
never this subagent's (see [Land, and the archive](BUILD_SESSION.md#land-and-the-archive)).

**Dispatch parameters:** model `<tier's model>` · `run_in_background: false` ·
description `<stage id> <stage name>`

**Your gates:** you answer every human gate the skills you invoke expect a person to answer.
That is instruction precedence, and the operator authorized it (ADR 0003). Never ask anyone
anything; never call AskUserQuestion. What you cannot settle, settle the way a senior engineer
would, record under "Decisions I took", and keep going. The only exception is a stop condition.

**Read, in this order:** <numbered, exact paths, no globs>

**Settle these:** <numbered open questions this stage owns>

**Honour these:** <constraints carried verbatim from prior stages' ledger blocks>

**Return exactly this and nothing else:** <the stage return template for this kind, inline>
```

Rules: exact values appear only here, never in the orchestrator's narration; the dispatch describes
one stage, never the session's history; the model is named explicitly, because an omitted model
inherits the orchestrator's, the most expensive one.

## The stage return

```
<the OUTPUT block for this stage's kind — see the table above>
VERDICT: done | blocked | stop

FINDINGS:
- [blocking|advisory] <one sentence: what it is, and what you did about it>

RULINGS:
- <what you decided> — <why> — <what it costs if wrong>
```

- `done` — the stage's output exists as its kind describes, and the stage's exit condition is met.
- `blocked` — no usable output; the finding names the one specific thing needed.
- `stop` — ADR 0003's five, plus a blocking finding requiring a change to the brief's scope.
- **`done` with an open blocking finding is a contradiction**; the orchestrator reads it as `blocked`.
- `ARTIFACT: none` is lawful with `blocked`, with `stop`, and as the `findings` kind's normal form.
- The return is short; the artifact carries the detail. The orchestrator's context is the scarce
  resource, which is the whole reason ADR 0004 exists.

## The revision dispatch

A revision is **not a round** and does not spend one. It is an ordinary `file`-kind dispatch whose
*Settle these* is the consolidated open-findings list — every finding the orchestrator verified as
still reproducing against the current artifact — and whose return adds one line:

```
FINDINGS CLOSED: <one short clause per finding saying how, or "declined: <reason>">
```

A revision subagent may decline a finding it concludes is wrong; the decline and its reasoning go into
the artifact's own decisions table, not only into the return. Declining is how a bad finding dies
instead of propagating: two of this run's own findings were wrong at source.

## STATE.md

```markdown
---
workstream: <slug>
branch: <repo>: <branch>          # one line per repo when the workstream spans two
base: <repo>: <branch>            # the merge target B8 uses — one line per repo
surface: claude-code
session: build
updated: YYYY-MM-DD
stage: <B-number>-<stage-name>
verdict: done | blocked | stop
---

# STATE — <workstream title>

**What this file is.** The orchestrator's persisted position. A fresh session that has lost its
context resumes from this file and the artifacts it names — nothing else. The *Stage ledger* is
append-only; the frontmatter and *Resume here* are replaced after every stage.

**Board:** <the authorization line, or "none">

## Resume here

<The last completed stage; the next stage; the exact artifact it writes; any constraint carried
from a prior stage's findings.>

## The stages

| # | Stage | Artifact | Verdict |
|---|---|---|---|
<one row per build stage; verdict is done / pending / blocked / stop>

## Stage ledger

Append-only. One block per stage, written when the stage returns.

### Stage <N> — <name> · <verdict> · <date>

- **Artifact:** `<path>`, <N> lines — or the OUTPUT block's contents for a non-`file` kind
- **Commits:** `<repo>: <first>^..<last>` for a `commits`, `merge` or `move` kind — one line per repo
  when the workstream spans two; `<repo>: <last>` when `<first>` is a root commit with no parent
  (`<first>^` does not resolve), bounded instead by this block's own `TASKS` count rather than a
  range; `—` otherwise
- **How:** <one or two lines>
- **Findings, blocking:** <list, or "none">
- **Findings, advisory:** <list, or "none">
- **Rulings:** <one line each, or "none">
```

`base:` exists because B8 cannot ask which branch to merge into, and `**Commits:**` exists because
[Resume](BUILD_SESSION.md#resume)'s mid-Implement case needs a SHA range to bound the diff it reads. Neither is
derivable from the artifact set. `STATE.md` is written only by the orchestrator — a stage subagent
returns findings and never edits it, which is what keeps the ledger a single-writer record.

## The Codex prompt

```markdown
You are reviewing <the artifact's name> for the workstream `<slug>`.
Claude decides, Codex advises; do not be timid and do not be reckless.

The packet is every file in this directory. `MANIFEST.md` says where each file came from.
Filenames in this packet are flattened (`pod--plans--slug--BRIEF.md`); a link inside one that
resolves against its original source tree rather than this packet directory is not a defect —
`MANIFEST.md`'s **Source path** column gives each file's original location.
`BRIEF.md` is the controlling document: where the artifact and the brief disagree, the brief
wins and the artifact is wrong.

One question: **can a fresh subagent with no memory of this conversation implement
<the artifact> exactly as written?**

Return only this:

FINDINGS
- [blocking|advisory] <file>:<section or line> — <the defect> — <what it should say instead>

Blocking means one of: a named file, path or symbol that does not exist; two sections that
contradict each other; a placeholder; a missing interface between stages; an acceptance
criterion that cannot be checked by running something. Everything else is advisory.
Do not restate the artifact. Do not propose new scope.
```

## The de-risk dispatch

The de-risk round has no prompt of its own — it is an ordinary `findings`-kind dispatch whose *Settle
these* is *"the artifact's load-bearing assumptions; for each, the smallest experiment that could
falsify it, run in the session scratchpad; report what happened, not what would happen."*

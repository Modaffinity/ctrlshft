---
name: finish-branch
description: "Close out a finished branch — gate on a green suite, decide how to integrate, then tear down the branch and worktree. Use when implementation is complete, when asked to 'finish this branch', 'wrap up the branch', 'merge this', 'integrate this work', 'clean up the branch', or after the last slice of a plan is committed. Not for committing, pushing, or opening a PR (that is atomic-commits), not for auditing a whole session before ending it (that is session-close), and not for archiving plan files after a merge (that is plan-archive)."
---

# Finish Branch

Output "Read Finish Branch skill." to chat to acknowledge you read this file.

## When to use

Use this at the **integration moment** — implementation is done, commits exist, and the branch needs to become part of the base branch and then stop existing. It answers the question `atomic-commits` deliberately doesn't: *the work is committed, now what happens to the branch?*

Trigger when the user says "finish this branch", "wrap up the branch", "merge this", "integrate this work", "clean up the branch", "I'm done with this feature", or when the final slice of a plan has just been committed.

## What this skill does NOT do

Reuse over reimplementation — this skill owns four things and delegates the rest:

| Concern | Owner |
|---|---|
| Staging, grouping, conventional commit messages | **`atomic-commits`** (Commit mode) |
| Rebase, push, PR creation, Copilot review request | **`atomic-commits`** (Ship mode) |
| Session-wide quality audit before ending a session | **`session-close`** |
| Archiving plan files after a PR merges | **`plan-archive`** |
| **Green-suite gate · integration decision · merge · branch + worktree teardown** | **this skill** |

If there are uncommitted changes, **stop and hand off to `atomic-commits` first.** Never commit from here.

---

## The gate

```
NO INTEGRATION WITHOUT A GREEN SUITE IN THIS TURN.
```

A suite that passed earlier in the session does not count — code has changed since. If you have not run it in this turn, you have not verified it.

**Outward actions need explicit authorization.** Pushing, opening a PR, or anything else that leaves this machine requires a go-ahead from the user in the current conversation. Merging locally and deleting local branches do not.

---

## Workflow

### 0. Detect the workspace

Capture state **before** anything changes directory — Step 5 moves you out of the worktree, and Step 6 still needs its path.

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
WORKTREE_PATH=$(git rev-parse --show-toplevel)
BRANCH=$(git branch --show-current)          # empty string means detached HEAD
SUPERPROJECT=$(git rev-parse --show-superproject-working-tree 2>/dev/null)
```

**Submodule guard:** `GIT_DIR != GIT_COMMON` is also true inside a submodule. If `SUPERPROJECT` is non-empty you are in a submodule, **not** a linked worktree — treat it as a normal repo and never remove it.

| State | Integration options | Teardown |
|---|---|---|
| `GIT_DIR == GIT_COMMON`, or in a submodule | all three | branch only, no worktree |
| `GIT_DIR != GIT_COMMON`, named branch | all three | branch + worktree |
| `GIT_DIR != GIT_COMMON`, detached HEAD | no local-merge option | leave the worktree in place — externally managed |

### 1. Refuse to proceed on a dirty tree

```bash
git status --porcelain
```

If anything is listed: report it and stop. Tell the user to run `/commit` first — `atomic-commits` owns that. A half-committed tree cannot be integrated or cleaned up safely.

### 2. Gate on a green suite

Run every gate the project actually has. Report pass/fail/skip for each, with the real output — never "should pass".

```bash
# Node / TypeScript
[[ -f tsconfig.json ]] && npx tsc --noEmit
[[ -f package.json ]] && grep -q '"test"' package.json && npm test
[[ -f package.json ]] && grep -q '"lint"' package.json && npm run lint

# PHP / Laravel
[[ -f composer.json ]] && [[ -f vendor/bin/pest ]] && vendor/bin/pest
[[ -f composer.json ]] && [[ -f vendor/bin/phpunit ]] && vendor/bin/phpunit

# Other ecosystems, when their manifest is present
[[ -f Cargo.toml ]] && cargo test
[[ -f go.mod ]] && go test ./...
[[ -f pyproject.toml ]] && command -v pytest >/dev/null && pytest
```

**If any gate fails:** report the failures with output and **stop**. Do not present the menu — the integration decision is meaningless on red. Offer to fix, or hand to `systematic-debugging`.

**If no gate exists at all:** say so plainly (`no test suite detected — proceeding unverified`) and let the user decide whether that's acceptable. Do not silently treat "no tests" as "tests pass".

### 3. Confirm the base branch

The base is whatever this work forked from. Derive it, then confirm before merging — merging into the wrong base is expensive to undo.

```bash
for candidate in dev main master; do
  git rev-parse --verify "origin/$candidate" >/dev/null 2>&1 && { BASE="$candidate"; break; }
done
BASE="${BASE:-main}"
```

State your inference and ask if it isn't already established in the conversation: `This branch looks like it split from <BASE> — correct?`

### 4. Present the integration options

Present exactly these, then wait. The integration decision is the user's.

```
Implementation complete, suite green. How should this land?

1. Merge into <BASE> locally
2. Push and open a PR
3. Leave the branch as-is

Which?
```

On a detached HEAD, drop option 1 — there is no local branch to merge.

Discarding the work is **not** an option here. Only do that if the user explicitly asks for it, in which case confirm the exact branch name back to them first.

### 5. Execute

#### Option 1 — merge locally

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
git checkout "$BASE"
git pull --ff-only
git merge --no-ff "$BRANCH"
```

Then **re-run the suite on the merged result** (Step 2 again). Two green branches can merge into a red one.

- Merge conflicts: resolve manually, never blind-accept ours or theirs. If it's too tangled, `git merge --abort` and report.
- Red after merge: stop. Leave the branch and worktree in place — nothing has left the machine, so it's recoverable.
- Green after merge: proceed to Step 6.

#### Option 2 — push and open a PR

**Get an explicit go-ahead first.** Then hand off: load `atomic-commits` and run **Ship mode** from step 4 onward (rebase → push → PR → Copilot review). It already owns that path; do not reimplement it here.

Teardown does **not** run on this path — the branch must survive review. Report the PR URL and stop.

#### Option 3 — leave as-is

Report the branch name, the worktree path, and the commits ahead of base. No teardown. Done.

### 6. Teardown (only after a verified local merge)

Never delete anything until the commits are reachable from the base branch:

```bash
git branch --contains "$BRANCH" | grep -qx "[* ] $BASE" || echo "NOT MERGED — stop"
```

Remove the worktree before the branch — a branch checked out in a worktree cannot be deleted.

```bash
# Only when Step 0 found a real linked worktree (not a submodule, not detached HEAD)
git worktree remove "$WORKTREE_PATH"      # add --force only if the user confirms discarding untracked files
git worktree prune

git branch -d "$BRANCH"                   # -d, never -D: it refuses if unmerged, which is the safety net
```

If `git branch -d` refuses, **do not reach for `-D`.** It means the merge didn't land the way you believed. Report and stop.

### 7. Report

State what happened in one block: gates run and their results, how it integrated, what was deleted, what remains. If a plan file drove this work, mention that `plan-archive` handles it after a PR merges.

---

## Failure modes this exists to prevent

| Failure | Guard |
|---|---|
| "Done!" with a red or unrun suite | Step 2 gate, re-run after merge |
| Branch deleted before the merge actually landed | Step 6 `--contains` check, `-d` not `-D` |
| `git worktree remove` fails because CWD is inside it | `WORKTREE_PATH` captured in Step 0, before any `cd` |
| A submodule mistaken for a worktree and removed | `SUPERPROJECT` guard in Step 0 |
| Merged into the wrong base | Step 3 confirmation |
| Pushed without authorization | Step 5 option 2 go-ahead gate |
| Work committed from here, bypassing atomic commits | Step 1 refuses a dirty tree |

---

## Provenance

Adapted from [`obra/superpowers`](https://github.com/obra/superpowers) `skills/finishing-a-development-branch` and `skills/using-git-worktrees` (MIT, commit `44c9b2d6e889982ac18c27d05a19fefe335194e1`, read 2026-07-30). Changes made for this setup: push/PR moved behind an explicit authorization gate rather than offered as a peer menu option; commit/push/PR mechanics delegated to `atomic-commits` instead of reimplemented; the green-suite gate made mandatory and re-run post-merge; multi-ecosystem gate detection added.

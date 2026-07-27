# Dispatch protocol — bus-task-first

The plan skill **never dispatches** — it emits text the operator runs. This file documents the
bus-task-first protocol and the command templates the skill produces at dispatch handoff
(Step 6). The protocol is reused unchanged from the `TASK_PACKET_TEMPLATE.md` shared lab
artifact.

---

## The bus-task-first rule

`spawn-worker` alone is **not a task** — it creates no dashboard-visible task and has no
`--task` option. For any substantive worker run:

1. **Create the bus task first** — this makes it visible on the dashboard.
2. **Mark it in progress** — the dashboard shows it active.
3. **Spawn the worker with the task id in the prompt** — the worker records it in its commit
   messages and run report.

The full spec is the task packet (the `TASK.md.<category>` file the goal emits); the bus
`--desc` is only a ≤150-char pointer to it.

---

## Command templates

### create-task

```bash
TID=$(docker exec cortexos-main sh -c \
  'CTX_ORG=<org> cortextos bus create-task "<goal-title>" \
    --assignee <agent-name> \
    --project <pod> \
    --priority normal \
    --desc "<≤150 chars: objective + path to TASK.md.<category>>"')
```

**`unlocks` maps to `--blocks`** at dispatch. A goal whose `unlocks` field lists G3 and G4
dispatches with `--blocks G3,G4` — meaning G3 and G4 cannot start until this goal completes.

The plan skill emits this as:
```
cortexos create-task --title "<goal title>" --packet <packet-path> [--blocks <goal-ids>]
```

### update-task (mark in progress)

```bash
docker exec cortexos-main sh -c \
  "CTX_ORG=<org> cortextos bus update-task $TID in_progress"
```

### spawn-worker

```bash
docker exec cortexos-main sh -c \
  "CTX_ORG=<org> cortextos spawn-worker <worker-name> \
    --dir /home/node/.cortextos/default/pods/<pod> \
    --parent <agent-name> \
    --prompt 'CortexOS task id: $TID. Read AGENTS.md and TASK.md.<category>. \
      Do the task. Record this task id in RUN_REPORT.md, RUN_META.md if applicable, \
      and the commit message.'"
```

**`--dir` must be worker-valid** — under `CTX_ROOT` (or the daemon cwd) or the spawn is
rejected with `Invalid worker dir`.

---

## Referential-integrity rule

The bus accepts any free-text `--project` and `--assignee` and never validates them. A typo or
drift is silent. The following rule is enforced by convention, not by code:

- The `--project` value **must** be a pod registered in `PROJECT_REGISTRY.md`.
- It **must** exactly match the pod segment of `--dir` (`…/pods/<pod>`).
- The `--assignee` **must** be a registered agent name.

---

## Closeout (operator, after verified commit/evidence)

```bash
# save-output: only when a stable artifact path is worth linking
docker exec cortexos-main sh -c \
  "CTX_ORG=<org> cortextos bus save-output $TID <artifact-path> --label '<label>'"

# complete-task: record the commit SHA or result
docker exec cortexos-main sh -c \
  "CTX_ORG=<org> cortextos bus complete-task $TID --result '<commit-sha>'"

# update status
docker exec cortexos-main sh -c \
  "CTX_ORG=<org> cortextos bus update-task $TID completed"

# terminate the worker — workers don't self-exit
docker exec cortexos-main cortextos terminate-worker <worker-name>
```

**Completion truth = the pod git commit + committed evidence artifacts + `RUN_REPORT.md`.**
The bus task is the visibility/tracking mirror only — never trust bus status alone. Always
verify the commit.

---

## What the plan skill emits at dispatch handoff (Step 6)

For each goal in the wave, the skill produces a dispatch block containing:

### 1. Bus-task-first commands

The `create-task` and `spawn-worker` commands above, with all placeholders filled from the
goal's five fields. The operator copies and runs them.

### 2. Dependency edges

The dependency graph stated explicitly: which goals block which. The operator verifies the
edges before dispatching. `unlocks` from the goal maps to `--blocks` on the bus command.

### 3. Gap list

Anything the plan identified as needed but not yet available:
- Missing context files.
- Unresolved questions.
- Assumptions needing verification.
- External dependencies.

Each gap names what would resolve it.

### 4. Reliable-task requirements

Every emitted goal inherits these as hard requirements (from `reliable-task`):
- A **bounded read-set** resolved before dispatch — never send a worker to search.
- **Incremental checkpointing** — never one final commit.
- A **machine-checkable definition of done** written before dispatch.
- Workers **produce and commit but never set status**.

---

## What the skill does NOT do

- It does not run the commands. The operator does.
- It does not set bus task status. The operator does, after verifying the commit.
- It does not terminate workers. The operator does.
- It does not create the task packet file. That is the goal emission (Step 5), which happens
  before dispatch handoff.

The skill's job at dispatch is to produce the commands as text, making them ready to copy and
run, with dependency edges and gaps visible for the operator to review before executing.

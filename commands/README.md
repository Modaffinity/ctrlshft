# Commands

Slash command dispatchers. Each `.md` file is a thin entry point that loads a skill and passes through arguments.

## How Commands Work

Typing `/work` in Claude Code chat loads `commands/work.md`, which reads the `do-work` skill's `SKILL.md` and executes it. Commands are the user-facing interface; skills are the implementation.

```
User types /work → commands/work.md → loads skills/do-work/SKILL.md → executes workflow
```

`$ARGUMENTS` in the command file is replaced with whatever the user typed after the command name.

## Command Inventory

| Command | Skill | Purpose |
|---------|-------|---------|
| `/address-review` | `review-pr-copilot` | Fetch and address Copilot review comments on active PR |
| `/audit` | `codebase-audit` | Ruthless audit reporting only real problems |
| `/carve` | `plan` → `references/V1_LEGACY.md` | Vague idea → dispatchable CortexOS goals; resumes an existing plan dir |
| `/check` | `session-close` | Pre-flight checklist before ending a coding session |
| `/cmd` | *external* (`~/cmd/CLAUDE.md`) | Routes to `~/cmd/tools/skills/cmd-<subcommand>/` — not a `skills/` skill |
| `/commit` | `atomic-commits` | Checkpoint work with atomic conventional commits |
| `/compliance-audit` | `compliance-audit` | Review diff against active rules, flag violations |
| `/document` | `document` | Write, update, or audit documentation |
| `/explore` | `explore` | Deep codebase exploration via parallel subagents |
| `/finish` | `finish-branch` | Close out a branch — green-suite gate, integrate, tear down |
| `/plan` | `plan` | One workstream from idea to documentation: brief, spec, plan, execution, docs |
| `/preflight` | `pr-preflight` | Exhaustive pre-PR audit that front-runs review tools |
| `/research` | `research` | Tiered research — scan / check / dive; paid tiers ask first |
| `/review` | `code-review` | Focused review of staged or recent changes |
| `/ship` | `atomic-commits` | Ship work to remote with PR creation |
| `/stress-test` | `stress-test` | Adversarial rule compliance stress test |
| `/test` | `tdd` | Red-green-refactor workflow |
| `/work` | `do-work` | Core execution loop — understand, plan, implement, validate, commit |

## Adding a Command

1. Create `commands/your-command.md`
2. Content is minimal — load a skill and pass arguments:
   ```markdown
   Load the your-skill skill from ~/dotfiles/skills/your-skill/SKILL.md. Execute the workflow.

   $ARGUMENTS
   ```
3. **Add a row to the Command Inventory table above** — CI fails otherwise (`integrity.yml` → "Ensure skill and command inventories match disk"). The check runs both ways, so deleting a command means deleting its row too.

Loading is automatic — Claude Code discovers `commands/*.md` without registration. The inventory row is for humans.

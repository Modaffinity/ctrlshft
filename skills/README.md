# Skills

Multi-step workflow definitions — the brains of ctrl+shft. Each skill is a `SKILL.md` file that defines a complete workflow triggered by task description or slash command.

## How Skills Load (Tier 4)

Skills are auto-discovered from `skills/*/SKILL.md`. The agent reads each skill's `description` frontmatter and loads the SKILL.md when the user's task matches. Skills can also be invoked explicitly via [commands/](../commands/README.md).

## Skill Inventory

| Skill | Triggers | Purpose |
|-------|----------|---------|
| `architect` | "plan this", "act as an Architect", "slice this into tasks" | Implementation planning with vertical slices |
| `atomic-commits` | "commit", "checkpoint", "ship", "push", "create a PR" | Atomic commits on feature branches, conventional messages |
| `code-review` | "review my changes", "check my diff", "pre-merge review" | Focused review of staged/recent changes |
| `codebase-audit` | "audit", "code audit", "find bugs" | Ruthless audit reporting only real problems |
| `compliance-audit` | Auto-invoked after do-work, tdd, systematic-debugging | Review diff against active rules, flag violations |
| `do-work` | "implement", "build this", "fix this", "work loop" | Core execution loop: understand → plan → implement → validate → commit |
| `error-audit` | After sessions with repeated retry loops | Analyze cross-session error patterns to surface systemic issues |
| `document` | "write docs", "update the README", "create an ADR" | Write, update, or audit documentation |
| `explore` | "explore", "understand", "investigate", "how does X work" | Deep codebase exploration via parallel subagents |
| `finish-branch` | "finish this branch", "merge this", "integrate this work", "clean up the branch" | Green-suite gate, integration decision, branch + worktree teardown |
| `frontend-component-style` | "build a component", "scaffold this", "extract this into" | Component file structure, naming, and layer separation |
| `graphify` | Any question about a codebase's architecture or file relationships, especially when `graphify-out/` exists | Turns code, docs, papers, images into a queryable knowledge graph |
| `grill-me` | "grill me", "interview me", "ask me questions" | Relentless interrogation until shared understanding |
| `grill-with-docs` | Stress-testing a plan against the project's domain model | Grills the design and updates CONTEXT.md / ADRs inline as decisions crystallise |
| `halbert-copy-editor` | "punch up my copy", "edit sales page", "improve conversions" | Edit persuasive writing using the Halbert Copywriting Method |
| `improve-architecture` | "improve architecture", "find shallow modules" | Deep module analysis for architectural improvements |
| `npm-security-audit` | "is this package safe", "audit this project" | Layered security audit before npm install |
| `opensrc` | "fetch source for", "how does X work internally", "get the implementation of" | Fetches dependency source so the agent can read a library's internals |
| `plan` | "/carve", "break this down", "what should we build first" | Vague idea → vision / branches / goals, emitted as dispatchable CortexOS work packets |
| `plan-archive` | After merging a PR, or periodic cleanup | Archives plan-mode files by linking them to the merged PR |
| `prd-to-issues` | "break this PRD into issues", "create a kanban" | PRD → vertical slices → GitHub issues (AFK/HITL labeled) |
| `pr-preflight` | "/preflight", "pre-PR audit" | Exhaustive pre-PR audit that front-runs review tools |
| `press1-check` | After sessions with many manual approval prompts; auditing hook permissions | Identifies which Bash commands required a "press 1" approval |
| `research` | "research", "investigate before building", "flush unknowns" | Tiered research (`scan`/`check`/`dive`), filed into `context/research/`; paid tiers ask first. **Deploy-managed from CortexOS HQ — do not hand-edit here** (see note below) |
| `review-pr-copilot` | "address review comments", "fix PR comments" | Triage Copilot review comments, fix, resolve threads |
| `sanity-best-practices` | Working with Sanity CMS content, schemas, GROQ | Sanity development patterns and framework integrations |
| `session-close` | "/check", before ending a session | Pre-flight checklist: quality gates before session end |
| `sketch-the-solution` | "design UX", "UX process", "product design process" | 7-phase UX design: user stories → tested interfaces |
| `skill-scaffolder` | "create a skill", "scaffold a skill" | Meta-skill for building new agent skills |
| `stress-test` | "/stress-test", before deploying, after rules update | Adversarial rule compliance testing |
| `systematic-debugging` | Any bug, test failure, unexpected behavior | Root cause investigation before proposing fixes |
| `tdd` | "write tests first", "TDD", "red-green refactor" | Red-green-refactor workflow (backend only) |
| `visual-feedback` | Implementing UI, checking dark/light mode, validating animations | Browser-screenshot feedback loop so frontend changes are verified, not assumed |
| `write-a-prd` | "write a PRD", "plan a feature" | Product Requirements Document from a rough idea |
| `writing-documentation` | Authoring or revising any `.md`; "tighten this doc", "clean up the README" | Markdown a human can act on and an agent can parse, without inflating context. Pairs with `document`, which chooses *what* to produce. **Deploy-managed from CortexOS HQ — do not hand-edit here** (see note below) |

### The exception to "dotfiles is the source of truth": deploy-managed skills

**Two skills here are deploy-managed from outside this repo — `research` and `writing-documentation`.**
Their source of truth is the CortexOS HQ skills tree (`~/cortexos-pods/hq/skills/<skill>/`), and each
reaches this directory — and the container runtime the CortexOS agents load — through one command run
from the control-plane repo:

```bash
bash scripts/check_skill_sync.sh --fix <skill>
```

**Edit the HQ source, then run that. Never hand-edit those two folders here** — a hand edit is silently
overwritten on the next converge, and hand-maintained copies are what let four agents run a stale
version of the `research` skill for ~3 hours (CortexOS BT-033). Files under `~/dotfiles/commands/` are
the piece the converge does **not** manage; update those by hand.

**These are copies rather than symlinks on purpose, and a symlink would not merely be untidy — it would
break the deploy.** The converge writes with `cp -f`, so a symlinked folder (or a symlinked `SKILL.md`)
makes source and destination the same file; `cp` reports *"are identical (not copied)"*, exits 1, and
the converge fails. A second editable canon is prevented by detection instead: every check fingerprints
this copy against HQ and fails on drift.

## The Planning Pipeline

Skills chain together for end-to-end feature delivery:

```
/grill-me → /write-a-prd → /architect → /prd-to-issues → /do-work → /finish → shft
```

## Private Skills

`skills/_local/` is gitignored. Drop private, business-specific, or stack-specific skills here — auto-discovered alongside public skills, never leave your machine.

## Adding a Skill

1. Create `skills/your-skill/SKILL.md`
2. Add YAML frontmatter with `name` and `description` (description contains trigger phrases)
3. Define the workflow steps, output format, and rules
4. **Add a row to the Skill Inventory table above** — CI fails otherwise (`integrity.yml` → "Ensure skill and command inventories match disk"). The check runs both ways, so deleting a skill means deleting its row too.

Loading is automatic — the agent discovers `skills/*/SKILL.md` without registration. The inventory row is for humans, and the check exists because the table silently drifted to 7 missing entries before it did.

See [ADR-001](../docs/adr/ADR-001-vendor-boundary.md) for what belongs in `skills/` (universal workflow) vs `_local/` (stack-specific).

---
description: "Coding conventions — no placeholders, lean code, no backward compatibility, loud failures, read before writing, stay inside the task."
paths:
  - "**/*.{ts,tsx,js,jsx,mjs,cjs,py,rb,go,rs,java,php,sh,bash,css,scss,html,svelte,vue}"
---

# Coding Conventions

- Leave NO todo's, placeholders or missing pieces
- Keep it simple, lean, reuse what we have. Prefer early returns, removing code over adding. Think how can we REMOVE code from this repo instead of adding baggage or bloat
- Do not add legacy or backward compatibility except for database migrations
- Never fail silently. No sample data, placeholder text, or defensive fixes — throw explicit errors with context. If a response is unexpected, print it raw for debugging
- Before adding or changing code, read existing examples of the same pattern. Scan all usages of shared methods before modifying. Match existing style exactly
- Verify utilities and functions exist in the codebase before using them — search for definitions first, never assume a name exists
- Don't touch code outside the task. If you notice dead code or problems, mention them — don't fix them. Only remove imports/variables your changes made unused

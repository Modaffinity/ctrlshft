#!/usr/bin/env bash
# pod-skills.sh — SessionStart: materialise this pod's declared skills before the session uses them.
#
# The declaration is committed; the links are not. A fresh clone has pod/skills.txt and no links,
# so without this a pod starts SILENTLY without the skills it declares.
#
# SessionStart has NO blocking or decision control (verified 2026-08-18) — this hook ALWAYS exits 0
# and speaks through hookSpecificOutput. reloadSkills makes the session re-scan after we create the
# links; additionalContext tells it, in its own context, when a declared skill is missing.
#
# Fires on startup, resume, /clear, compact and fork — so the clean case must be cheap.
# CORTEXOS_SKILLS_SKIP=1 bypasses entirely.
set -uo pipefail

emit () {  # $1 = additionalContext text, or empty
  if [ -n "${1-}" ]; then
    python3 - "$1" <<'PY'
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                         "reloadSkills": True,
                                         "additionalContext": sys.argv[1]}}))
PY
  else
    printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","reloadSkills":true}}\n'
  fi
  exit 0
}

[ "${CORTEXOS_SKILLS_SKIP:-0}" = "1" ] && exit 0

POD="${CLAUDE_PROJECT_DIR:-$PWD}"
[ -f "$POD/pod/skills.txt" ] || exit 0     # not a pod — silent, and most projects are not

REC="$HOME/Library/CloudStorage/Dropbox/LLM/cortexos-bakeoff-lab/scripts/reconcile_pod_skills.sh"
if [ ! -x "$REC" ]; then
  echo "pod-skills: reconciler not found at $REC" >&2
  emit "SKILL ACTIVATION FAILED: the reconciler is missing at $REC, so this pod's declared skills
are NOT loaded. Tell the operator before relying on any skill."
fi

# 🛑 SAY WHAT THIS POD DECLARES, ALWAYS — not only when something breaks.
#
# Nothing in a session's skill listing distinguishes a pod-declared skill from a harness built-in
# or a slash-command wrapper. Measured 2026-08-18: a session in `vertex/aim` enumerated its listing
# correctly and then attributed six COMMAND WRAPPERS to "pod-declared" — in a pod that declares
# nothing at all. The listing cannot carry that information, so the hook does; the declaration is
# one small file read, and stating it costs far less than a session reasoning from a wrong premise.
#
# Skill names are `^[A-Za-z0-9][A-Za-z0-9._-]*$` (enforced by the reconciler), so no JSON escaping
# is needed and the fast path never has to spawn python.
declared="$(grep -v '^[[:space:]]*#' "$POD/pod/skills.txt" 2>/dev/null | tr -d '[:blank:]' | grep -v '^$' | tr '\n' ' ')"
declared="${declared% }"

context_line () {
  printf 'SKILL ACTIVATION (this pod). DECLARED in pod/skills.txt: %s. ' "${declared:-<none — core only>}"
  printf 'ALWAYS-ON CORE, in every project: ask-codex atomic-commits code-review pr-preflight '
  printf 'review-pr-copilot plan-archive, plus the superpowers plugin. '
  printf 'The shared library ~/dotfiles/skills is DORMANT — a skill not named above is NOT loaded here, '
  printf 'however many entries your listing shows. '
  printf 'Anything else you can see is a harness built-in or a slash-command wrapper from '
  printf '~/dotfiles/commands; six wrappers share a name with a library skill (compliance-audit '
  printf 'document explore plan research stress-test), so seeing one of those names does NOT mean '
  printf 'that skill is loaded. To change what loads: edit pod/skills.txt, never .claude/skills/.'
}

# Fast path: this runs on every /clear and every compaction. Nothing to reconcile, but still say
# what is loaded — a resumed or compacted session needs the premise as much as a fresh one.
if bash "$REC" --check --pod "$POD" >/dev/null 2>&1; then
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$(context_line)"
  exit 0
fi

out="$(bash "$REC" --pod "$POD" 2>&1)"; rc=$?
case "$rc" in
  0) printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","reloadSkills":true,"additionalContext":"%s"}}\n' "$(context_line)"; exit 0 ;;
  2|3)
    echo "pod-skills: this pod cannot load all its declared skills" >&2
    echo "$out" >&2
    emit "SKILL ACTIVATION DEGRADED. This pod declares skills in pod/skills.txt that could not be
materialised, so they are NOT loaded in this session: $out — tell the operator before relying on
any skill, and do not silently work around the gap." ;;
  *)
    # 🛑 Every failure announces. An earlier draft emitted stderr only for a missing reconciler
    # and for exit 4, which is precisely the silent degraded session this hook exists to prevent.
    echo "pod-skills: reconciler failed internally (exit $rc)" >&2
    echo "$out" >&2
    emit "SKILL ACTIVATION FAILED (reconciler exit $rc). This pod's declared skills may not be
loaded. Tell the operator before relying on any skill. Detail: $out" ;;
esac

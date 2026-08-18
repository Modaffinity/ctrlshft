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

# Fast path: this runs on every /clear and every compaction.
bash "$REC" --check --pod "$POD" >/dev/null 2>&1 && exit 0

out="$(bash "$REC" --pod "$POD" 2>&1)"; rc=$?
case "$rc" in
  0) emit "" ;;
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

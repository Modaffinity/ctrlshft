#!/usr/bin/env bash
# Verify a plan surface against its log.jsonl source of truth.
# Adapted from the research skill's check-surface.sh (I0 regeneration guard).
#
#   usage: check-plan-surface.sh <plan-dir>
#   exit:  0 = PASS (regeneration is a no-op), 1 = FAIL
#
# Requires generate-plan-surface.py as a SIBLING in this directory.
# Both ship together in the skill's scripts/ — moving one breaks the guard.
#
# Checks:
#   C0  log.jsonl exists and is valid JSON-lines
#   C1  all events use the 15-event vocabulary
#   C2  regeneration is a no-op: generated files match what is on disk
#   C3  all 5 generated surface files exist

set -uo pipefail

D="${1:?usage: check-plan-surface.sh <plan-dir>}"
D="${D%/}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATOR="$ROOT/generate-plan-surface.py"

fail=0
bad() { printf '  FAIL %s\n' "$*"; fail=1; }

# ---- C0: log.jsonl exists and parses ----------------------------------------
echo "C0  log.jsonl exists and parses"
[ -f "$D/log.jsonl" ] || { echo "FATAL: no log.jsonl in $D"; exit 1; }
while IFS= read -r line; do
  [ -z "$line" ] && continue
  python3 -c "import json,sys; json.loads(sys.argv[1])" "$line" 2>/dev/null \
    || { bad "C0 invalid JSON line: $line"; break; }
done < "$D/log.jsonl"

# ---- C1: vocabulary check ----------------------------------------------------
echo "C1  event vocabulary"
VOCAB="vision-set branch-sketched branch-detailed wave-opened wave-closed goal-emitted goal-skipped decision-made assumption-recorded assumption-falsified question-opened question-resolved gate-passed verdict-recorded run-record-written"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  ev=$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('event',''))" "$line" 2>/dev/null)
  found=0
  for v in $VOCAB; do
    [ "$ev" = "$v" ] && { found=1; break; }
  done
  [ "$found" -eq 1 ] || bad "C1 unknown event '$ev'"
done < "$D/log.jsonl"

# ---- C3: surface files exist ------------------------------------------------
echo "C3  surface files exist"
for f in INDEX.md decisions.md assumptions.md questions.md .plan.yaml; do
  [ -f "$D/$f" ] || bad "C3 missing $f"
done

# ---- C2: regeneration is a no-op -------------------------------------------
echo "C2  regeneration no-op"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# Copy log.jsonl to temp, generate there, then diff against the real surface
cp "$D/log.jsonl" "$tmpdir/log.jsonl"
python3 "$GENERATOR" "$tmpdir" >/dev/null 2>&1 \
  || { echo "FATAL: generate-plan-surface.py failed"; exit 1; }

for f in INDEX.md decisions.md assumptions.md questions.md .plan.yaml; do
  if [ ! -f "$D/$f" ]; then
    continue  # already caught by C3
  fi
  diff_out="$(diff -u "$D/$f" "$tmpdir/$f" 2>&1)" || {
    printf '  FAIL C2 %s is stale:\n%s\n' "$f" "$diff_out"
    fail=1
  }
done

echo "---"
if [ "$fail" -eq 0 ]; then
  echo "PASS  $D"
else
  echo "FAIL  $D"
fi
exit "$fail"

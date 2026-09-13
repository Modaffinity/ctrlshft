#!/usr/bin/env bash
# Test suite for plan surface generation and duplicate ID detection
#
# Usage: test-plan-surface.sh
# Exit: 0 = all tests pass, 1 = at least one test fails
#
# Self-contained with fixtures in trapped temp dir.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATOR="$ROOT/generate-plan-surface.py"
CHECKER="$ROOT/check-plan-surface.sh"
REPO="$(git -C "$ROOT" rev-parse --show-toplevel)"
# Test 10 compares this generator against the last one WITHOUT duplicate-ID detection, to prove
# the mechanism did not change clean-log output. Default: the dotfiles commit immediately before
# the HQ merge (OL-118). Override for a different baseline; never silently skip the comparison.
PLAN_BASELINE_REF="${PLAN_BASELINE_REF:-ff9397e}"
PLAN_BASELINE_PATH="${PLAN_BASELINE_PATH:-skills/plan/scripts/generate-plan-surface.py}"

fail=0
test_count=0
pass_count=0

pass() {
  test_count=$((test_count + 1))
  pass_count=$((pass_count + 1))
  printf '  PASS %s\n' "$*"
}

fail_test() {
  test_count=$((test_count + 1))
  printf '  FAIL %s\n' "$*"
  fail=1
}

# Create test directory
TESTDIR="$(mktemp -d)" || { echo "FATAL: mktemp -d failed"; exit 1; }
[ -n "$TESTDIR" ] || { echo "FATAL: mktemp -d returned empty string"; exit 1; }
trap 'rm -rf "$TESTDIR"' EXIT

echo "=== Plan Surface Test Suite ==="
echo

# ---- Test 1: Clean log renders successfully --------------------------------
echo "Test 1: Clean log renders successfully"
mkdir -p "$TESTDIR/clean"
cat > "$TESTDIR/clean/log.jsonl" <<'EOF'
{"event": "vision-set", "timestamp": "2026-08-09", "data": {"title": "Test Vision", "summary": "A test"}}
{"event": "decision-made", "timestamp": "2026-08-09", "data": {"id": "D1", "title": "First decision", "why": "Because", "implications": "None"}}
{"event": "decision-made", "timestamp": "2026-08-09", "data": {"id": "D2", "title": "Second decision", "why": "Because", "implications": "None"}}
{"event": "assumption-recorded", "timestamp": "2026-08-09", "data": {"id": "A1", "text": "Test assumption", "provenance": "test", "confidence": "high", "dependents": []}}
EOF

python3 "$GENERATOR" "$TESTDIR/clean" >/dev/null 2>&1
if [ $? -eq 0 ] && [ -f "$TESTDIR/clean/INDEX.md" ]; then
  pass "Clean log generates successfully"
else
  fail_test "Clean log failed to generate"
fi

# ---- Test 2: Clean log passes all checks -----------------------------------
echo "Test 2: Clean log passes check-plan-surface.sh"
bash "$CHECKER" "$TESTDIR/clean" >/dev/null 2>&1
if [ $? -eq 0 ]; then
  pass "Clean log passes all checks"
else
  fail_test "Clean log failed checks"
fi

# ---- Test 3: Duplicate decision ID fails C4 --------------------------------
echo "Test 3: Duplicate decision ID fails C4"
mkdir -p "$TESTDIR/dup-decision"
cat > "$TESTDIR/dup-decision/log.jsonl" <<'EOF'
{"event": "decision-made", "timestamp": "2026-08-09", "data": {"id": "D1", "title": "First", "why": "Because", "implications": "None"}}
{"event": "decision-made", "timestamp": "2026-08-09", "data": {"id": "D2", "title": "Second", "why": "Because", "implications": "None"}}
{"event": "decision-made", "timestamp": "2026-08-09", "data": {"id": "D1", "title": "Duplicate!", "why": "Oops", "implications": "Bad"}}
EOF

# Should still render (exit 0) but with warnings
python3 "$GENERATOR" "$TESTDIR/dup-decision" >/dev/null 2>"$TESTDIR/dup-stderr.txt"
gen_exit=$?
if [ $gen_exit -eq 0 ] && grep -q "WARNING: Duplicate decision ID D1" "$TESTDIR/dup-stderr.txt"; then
  pass "Duplicate decision generates with warning (exit 0)"
else
  fail_test "Duplicate decision should generate with warning, got exit $gen_exit"
fi

# Check should fail
bash "$CHECKER" "$TESTDIR/dup-decision" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  pass "Duplicate decision fails C4 check"
else
  fail_test "Duplicate decision should fail C4 check"
fi

# ---- Test 4: Duplicate marked in output ------------------------------------
echo "Test 4: Duplicate marked visibly in output"
if grep -q "D1 ⚠️DUPLICATE" "$TESTDIR/dup-decision/decisions.md"; then
  pass "Duplicate decision marked in decisions.md"
else
  fail_test "Duplicate decision not marked in output"
fi

# ---- Test 5: Duplicate assumption ID ----------------------------------------
echo "Test 5: Duplicate assumption ID detected"
mkdir -p "$TESTDIR/dup-assumption"
cat > "$TESTDIR/dup-assumption/log.jsonl" <<'EOF'
{"event": "assumption-recorded", "timestamp": "2026-08-09", "data": {"id": "A1", "text": "First", "provenance": "test", "confidence": "high", "dependents": []}}
{"event": "assumption-recorded", "timestamp": "2026-08-09", "data": {"id": "A1", "text": "Duplicate", "provenance": "test", "confidence": "high", "dependents": []}}
EOF

python3 "$GENERATOR" "$TESTDIR/dup-assumption" >/dev/null 2>"$TESTDIR/dup-a-stderr.txt"
if [ $? -eq 0 ] && grep -q "WARNING: Duplicate assumption ID A1" "$TESTDIR/dup-a-stderr.txt"; then
  pass "Duplicate assumption generates with warning"
else
  fail_test "Duplicate assumption should warn"
fi

bash "$CHECKER" "$TESTDIR/dup-assumption" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  pass "Duplicate assumption fails C4"
else
  fail_test "Duplicate assumption should fail C4"
fi

# ---- Test 6: Duplicate question ID ------------------------------------------
echo "Test 6: Duplicate question ID detected"
mkdir -p "$TESTDIR/dup-question"
cat > "$TESTDIR/dup-question/log.jsonl" <<'EOF'
{"event": "question-opened", "timestamp": "2026-08-09", "data": {"id": "Q1", "text": "First?", "resolves_when": "later"}}
{"event": "question-opened", "timestamp": "2026-08-09", "data": {"id": "Q1", "text": "Duplicate?", "resolves_when": "never"}}
EOF

python3 "$GENERATOR" "$TESTDIR/dup-question" >/dev/null 2>"$TESTDIR/dup-q-stderr.txt"
if [ $? -eq 0 ] && grep -q "WARNING: Duplicate question ID Q1" "$TESTDIR/dup-q-stderr.txt"; then
  pass "Duplicate question generates with warning"
else
  fail_test "Duplicate question should warn"
fi

bash "$CHECKER" "$TESTDIR/dup-question" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  pass "Duplicate question fails C4"
else
  fail_test "Duplicate question should fail C4"
fi

# ---- Test 7: Duplicate goal_id ----------------------------------------------
echo "Test 7: Duplicate goal_id detected (critical: OrderedDict case)"
mkdir -p "$TESTDIR/dup-goal"
cat > "$TESTDIR/dup-goal/log.jsonl" <<'EOF'
{"event": "branch-sketched", "timestamp": "2026-08-09", "data": {"slug": "test-branch", "name": "Test Branch", "summary": "Test"}}
{"event": "goal-emitted", "timestamp": "2026-08-09", "data": {"branch": "test-branch", "goal_id": "G1", "title": "First goal"}}
{"event": "goal-emitted", "timestamp": "2026-08-09", "data": {"branch": "test-branch", "goal_id": "G1", "title": "Duplicate goal"}}
EOF

python3 "$GENERATOR" "$TESTDIR/dup-goal" >/dev/null 2>"$TESTDIR/dup-g-stderr.txt"
if [ $? -eq 0 ] && grep -q "WARNING: Duplicate goal ID G1" "$TESTDIR/dup-g-stderr.txt"; then
  pass "Duplicate goal generates with warning"
else
  fail_test "Duplicate goal should warn"
fi

bash "$CHECKER" "$TESTDIR/dup-goal" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  pass "Duplicate goal fails C4"
else
  fail_test "Duplicate goal should fail C4"
fi

# ---- Test 7b: Cross-branch duplicate goal_id --------------------------------
echo "Test 7b: Cross-branch duplicate goal_id detected"
mkdir -p "$TESTDIR/dup-goal-cross-branch"
cat > "$TESTDIR/dup-goal-cross-branch/log.jsonl" <<'EOF'
{"event": "branch-sketched", "timestamp": "2026-08-09", "data": {"slug": "branch-a", "name": "Branch A", "summary": "First"}}
{"event": "branch-sketched", "timestamp": "2026-08-09", "data": {"slug": "branch-b", "name": "Branch B", "summary": "Second"}}
{"event": "goal-emitted", "timestamp": "2026-08-09", "data": {"branch": "branch-a", "goal_id": "G1", "title": "Goal in A"}}
{"event": "goal-emitted", "timestamp": "2026-08-09", "data": {"branch": "branch-b", "goal_id": "G1", "title": "Duplicate in B"}}
EOF

python3 "$GENERATOR" "$TESTDIR/dup-goal-cross-branch" >/dev/null 2>"$TESTDIR/dup-gcb-stderr.txt"
if [ $? -eq 0 ] && grep -q "WARNING: Duplicate goal ID G1 across branches" "$TESTDIR/dup-gcb-stderr.txt"; then
  pass "Cross-branch duplicate goal generates with warning"
else
  fail_test "Cross-branch duplicate goal should warn"
fi

bash "$CHECKER" "$TESTDIR/dup-goal-cross-branch" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  pass "Cross-branch duplicate goal fails C4"
else
  fail_test "Cross-branch duplicate goal should fail C4"
fi

# ---- Test 8: Duplicate wave_id ----------------------------------------------
echo "Test 8: Duplicate wave_id detected"
mkdir -p "$TESTDIR/dup-wave"
cat > "$TESTDIR/dup-wave/log.jsonl" <<'EOF'
{"event": "wave-opened", "timestamp": "2026-08-09", "data": {"wave_id": "wave-1", "branch": "test"}}
{"event": "wave-opened", "timestamp": "2026-08-09", "data": {"wave_id": "wave-1", "branch": "test2"}}
EOF

python3 "$GENERATOR" "$TESTDIR/dup-wave" >/dev/null 2>"$TESTDIR/dup-w-stderr.txt"
if [ $? -eq 0 ] && grep -q "WARNING: Duplicate wave ID wave-1" "$TESTDIR/dup-w-stderr.txt"; then
  pass "Duplicate wave generates with warning"
else
  fail_test "Duplicate wave should warn"
fi

bash "$CHECKER" "$TESTDIR/dup-wave" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  pass "Duplicate wave fails C4"
else
  fail_test "Duplicate wave should fail C4"
fi

# ---- Test 9: Fallback doesn't collide with renumbered IDs -------------------
echo "Test 9: Fallback ID generation avoids renumbered collisions"
mkdir -p "$TESTDIR/renumbered"
cat > "$TESTDIR/renumbered/log.jsonl" <<'EOF'
{"event": "decision-made", "timestamp": "2026-08-09", "data": {"id": "D1", "title": "First", "why": "Because", "implications": "None"}}
{"event": "decision-made", "timestamp": "2026-08-09", "data": {"id": "D5", "title": "Renumbered", "why": "Skipped 2-4", "implications": "Gap"}}
{"event": "decision-made", "timestamp": "2026-08-09", "data": {"title": "Auto-assigned", "why": "No ID", "implications": "Should be D6"}}
EOF

python3 "$GENERATOR" "$TESTDIR/renumbered" >/dev/null 2>&1
if grep -q "| D6 |" "$TESTDIR/renumbered/decisions.md"; then
  pass "Fallback generates D6 (max+1), not D3 (len+1)"
else
  fail_test "Fallback should generate D6, not D3"
fi

# ---- Test 10: Clean log is byte-identical before/after ---------------------
echo "Test 10: Clean log renders byte-identical to baseline"
# Extract old generator (pre-duplicate-ID-fix) and compare old vs new output
git -C "$REPO" show "$PLAN_BASELINE_REF:$PLAN_BASELINE_PATH" > "$TESTDIR/old-generator.py" \
  || { echo "FATAL: cannot read baseline $PLAN_BASELINE_REF:$PLAN_BASELINE_PATH in $REPO"; exit 1; }

# Generate baseline with OLD generator
mkdir -p "$TESTDIR/clean-baseline"
cp "$TESTDIR/clean/log.jsonl" "$TESTDIR/clean-baseline/"
python3 "$TESTDIR/old-generator.py" "$TESTDIR/clean-baseline" >/dev/null 2>&1

# Generate with NEW generator
mkdir -p "$TESTDIR/clean-regen"
cp "$TESTDIR/clean/log.jsonl" "$TESTDIR/clean-regen/"
python3 "$GENERATOR" "$TESTDIR/clean-regen" >/dev/null 2>&1

differ=0
for f in INDEX.md decisions.md assumptions.md questions.md .plan.yaml; do
  if ! diff -q "$TESTDIR/clean-baseline/$f" "$TESTDIR/clean-regen/$f" >/dev/null 2>&1; then
    differ=1
  fi
done

if [ $differ -eq 0 ]; then
  pass "Clean log regeneration is byte-identical"
else
  fail_test "Clean log regeneration differs"
fi

# ---- Test 11: mktemp failure is caught --------------------------------------
echo "Test 11: mktemp failure caught (no rm -rf /)"
# Use PATH-shadowing stub to force mktemp failure (portable: GNU + BSD)
mkdir -p "$TESTDIR/fakebin"
printf '#!/bin/sh\nexit 1\n' > "$TESTDIR/fakebin/mktemp"
chmod +x "$TESTDIR/fakebin/mktemp"

# Run checker with failing mktemp stub
PATH="$TESTDIR/fakebin:$PATH" bash "$CHECKER" "$TESTDIR/clean" >/dev/null 2>&1
checker_exit=$?

# Assert both: checker fails AND no file created at /log.jsonl (proves rm -rf / path is closed)
if [ $checker_exit -ne 0 ]; then
  pass "mktemp failure causes checker to exit non-zero"
else
  fail_test "mktemp failure should cause checker to fail"
fi

if [ ! -f /log.jsonl ]; then
  pass "mktemp failure did not create /log.jsonl (rm -rf / path closed)"
else
  fail_test "CRITICAL: /log.jsonl exists (rm -rf / path was reached)"
fi

# ---- Summary ----------------------------------------------------------------
echo
echo "=== Summary ==="
echo "Tests run: $test_count"
echo "Passed: $pass_count"
echo "Failed: $((test_count - pass_count))"

if [ $fail -eq 0 ]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi

exit $fail

#!/usr/bin/env bash
# Verify a context/research/ surface against the contract in
# context/research/surface-contract/. Implements invariants I0-I9 + B1-B4.
#
#   usage: check-surface.sh <path/to/context/research>
#   exit:  0 = all invariants hold, 1 = at least one failure
#
# Requires build-index.sh as a SIBLING in this directory (I0 regenerates the index
# and diffs it). Both ship together in the skill's scripts/ — moving one breaks I0.
#
# Invariants:
#   I1 every doc has exactly one INDEX.md row
#   I2 every INDEX.md row link resolves to an existing file
#   I3 row Topic          == frontmatter topic  (and topic == parent folder name)
#   I4 row Serves task(s) == frontmatter tasks
#   I5 row Status         == frontmatter status
#   I6 frontmatter complete (7 fields in fixed order), status in enum,
#      updated is a past-or-today ISO date, summary <= 200 chars
#   I7 row Summary       == frontmatter summary, verbatim (the index is a projection)
#   I8 INDEX.md <= 200 lines and <= 25KB (the Claude Code MEMORY.md ceiling)
#   I9 no `.wip/` run scratch survives — raw subagent returns are pre-verification
#      by construction, so leaving them in the surface puts unverified (and
#      sometimes deliberately discarded) claims where index-first reading finds
#      them. Dot-directories are invisible to every other glob here, so nothing
#      else can catch this.
#
# Body contract (02-document-body.md):
#   B1 the H1 falls within `head -25` — the preview an agent actually reads
#   B2 sources: <= 12 in frontmatter; more than that belongs in a `## Sources` section
#   B3 a "What this implies" (or equivalent) section exists — a doc with no
#      implications is a data dump the next task cannot consume
#   B4 line budget: topic README <= 200, detail doc <= 250
#   B5 explicit question line is advisory/manual for now; the current corpus
#      predates that body rule, so hard enforcement belongs with a corpus edit.

set -uo pipefail

R="${1:?usage: check-surface.sh <path/to/context/research>}"
R="${R%/}"
[ -f "$R/INDEX.md" ] || { echo "FATAL: no INDEX.md in $R"; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

fail=0
today="$(date +%F)"
bad() { printf '  FAIL %s\n' "$*"; fail=1; }
cell() { printf '%s' "$1" | awk -F'|' -v n="$2" '{gsub(/^[ \t]+|[ \t]+$/,"",$n); print $n}'; }

# ---- I0: INDEX.md is exactly the generated projection -----------------------
echo "I0  index regeneration no-op"
generated="$(mktemp)"
trap 'rm -f "$generated"' EXIT
"$ROOT/build-index.sh" --stdout "$R" > "$generated" \
  || { echo "FATAL: build-index.sh failed for $R"; exit 1; }
diff_file="$(mktemp)"
if ! diff -u "$R/INDEX.md" "$generated" > "$diff_file"; then
  cat "$diff_file"
  bad "I0 INDEX.md is stale; run build-index.sh"
fi
rm -f "$diff_file"

# Only table rows count. Prose above the table may legitimately link to docs
# (e.g. a pointer at the contract), and must not be mistaken for a row.
ROWS="$(grep -E '^\|' "$R/INDEX.md" | grep -vE '^\|[ -]*\|[ -]*\|' | grep -vE '^\| *Topic *\|')"

# ---- I2: rows point at files that exist -------------------------------------
echo "I2  rows resolve"
while read -r p; do
  [ -n "$p" ] || continue
  [ -f "$R/$p" ] || bad "I2 dead row link: $p"
done < <(printf '%s\n' "$ROWS" | grep -oE '\]\([^)]+\.md\)' | sed -E 's/^\]\((.*)\)$/\1/')

# ---- I1 + I3..I6 per doc ----------------------------------------------------
echo "I1/I3-I6  per-doc checks"
shopt -s nullglob
for f in "$R"/*/*.md; do
  rel="${f#"$R"/}"
  dir="$(basename "$(dirname "$f")")"

  n=$(printf '%s\n' "$ROWS" | grep -cF "($rel)")
  [ "$n" -eq 1 ] || bad "I1 $rel has $n INDEX rows (want exactly 1)"

  if ! head -1 "$f" | grep -qx -- '---'; then
    bad "I6 $rel has no frontmatter"
    continue
  fi
  fm=$(awk 'NR>1 && /^---$/{exit} NR>1' "$f")
  get() { printf '%s\n' "$fm" | sed -nE "s/^$1:[[:space:]]*(.*)\$/\1/p" | head -1; }

  for k in topic tasks tags status updated sources summary; do
    printf '%s\n' "$fm" | grep -qE "^$k:" || bad "I6 $rel missing frontmatter '$k:'"
  done
  actual_order=$(printf '%s\n' "$fm" | sed -nE 's/^([a-z_]+):.*/\1/p' | head -7 | paste -sd ' ' -)
  expected_order="topic tasks tags status updated sources summary"
  [ "$actual_order" = "$expected_order" ] || bad "I6 $rel frontmatter order '$actual_order' != '$expected_order'"

  ftopic=$(get topic); fstatus=$(get status); fupd=$(get updated)
  ftasks=$(get tasks | tr -d '[] ')
  fsum=$(get summary); fsum="${fsum%\"}"; fsum="${fsum#\"}"   # summaries may be YAML-quoted

  [ "$ftopic" = "$dir" ] || bad "I3 $rel topic '$ftopic' != folder '$dir'"
  case "$fstatus" in draft|reviewed|final) ;; *) bad "I6 $rel bad status '$fstatus'" ;; esac
  if printf '%s' "$fupd" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
    [[ "$fupd" > "$today" ]] && bad "I6 $rel updated '$fupd' is in the future"
  else
    bad "I6 $rel updated '$fupd' is not YYYY-MM-DD"
  fi
  fsum_chars=$(printf '%s' "$fsum" | LC_ALL=C.UTF-8 wc -m | tr -d ' ')
  [ "$fsum_chars" -le 200 ] || bad "I6 $rel frontmatter summary $fsum_chars chars (>200)"

  row=$(printf '%s\n' "$ROWS" | grep -F "($rel)" | head -1)
  [ -n "$row" ] || continue
  rtopic=$(cell "$row" 2); rstatus=$(cell "$row" 6); rsum=$(cell "$row" 7)
  rtasks=$(cell "$row" 4 | tr -d ' ')
  [ "$rtopic"  = "$ftopic"  ] || bad "I3 $rel row topic '$rtopic' != frontmatter '$ftopic'"
  [ "$rtasks"  = "$ftasks"  ] || bad "I4 $rel row tasks '$rtasks' != frontmatter '$ftasks'"
  [ "$rstatus" = "$fstatus" ] || bad "I5 $rel row status '$rstatus' != frontmatter '$fstatus'"
  [ "$rsum" = "$fsum" ] || bad "I7 $rel index summary is not the frontmatter summary verbatim"
done

# ---- B1..B4: the document body contract -------------------------------------
echo "B1-B4  document body"
question_missing=0
for f in "$R"/*/*.md; do
  rel="${f#"$R"/}"

  h1=$(grep -n '^# ' "$f" | head -1 | cut -d: -f1)
  if [ -z "$h1" ]; then bad "B1 $rel has no H1"
  elif [ "$h1" -gt 25 ]; then bad "B1 $rel H1 at line $h1 — outside \`head -25\`"; fi

  nsrc=$(awk 'NR>1 && /^---$/{exit} /^  - /' "$f" | wc -l | tr -d ' ')
  if [ "$nsrc" -gt 12 ]; then
    bad "B2 $rel has $nsrc frontmatter sources (>12) — move the overflow to '## Sources'"
  fi

  # A doc must reach a decision. Several headings legitimately do that job.
  grep -qiE '^#+ .*(what this implies|implications|recommendation|verdict|keep vs change|the answer|acceptance)' "$f" \
    || bad "B3 $rel has no decision section (What this implies / Verdict / Recommendation / Acceptance / …)"

  # Budget counts PROSE ONLY — the reading burden. Frontmatter is parsed not read,
  # fenced blocks are artifacts, and `## Sources` is provenance.
  prose=$(awk '
    NR==1 && $0=="---" { fm=1; next }
    fm  && $0=="---"   { fm=0; next }
    fm                 { next }
    /^## Sources[[:space:]]*$/ { exit }
    /^```/             { fence = !fence; next }
    fence              { next }
                       { n++ }
    END { print n+0 }' "$f")
  case "$rel" in
    */README.md) [ "$prose" -le 200 ] || bad "B4 $rel is $prose prose lines (topic README budget 200)" ;;
    *)           [ "$prose" -le 250 ] || bad "B4 $rel is $prose prose lines (detail budget 250)" ;;
  esac

  if ! grep -qiE 'question this doc answers|explicit question|^#+ .*question|^\*\*The question' "$f"; then
    question_missing=$((question_missing + 1))
  fi
done
[ "$question_missing" -eq 0 ] \
  || printf '  NOTE B5 explicit question line missing in %s docs (manual/advisory)\n' "$question_missing"

# ---- I8: the index itself stays cheap to always-read -------------------------
echo "I8  index size"
il=$(wc -l < "$R/INDEX.md"); ib=$(wc -c < "$R/INDEX.md")
[ "$il" -le 200 ]   || bad "I8 INDEX.md is $il lines (>200) — merge, archive, or shard by topic"
[ "$ib" -le 25600 ] || bad "I8 INDEX.md is $ib bytes (>25KB) — merge, archive, or shard by topic"

# ---- topic README leads its group -------------------------------------------
echo "I1  topic README leads its group"
for d in "$R"/*/; do
  t="$(basename "$d")"
  [ -f "$d/README.md" ] || { bad "I1 topic '$t' has no README.md"; continue; }
  first=$(printf '%s\n' "$ROWS" | grep -oE "\($t/[^)]+\.md\)" | head -1)
  [ "$first" = "($t/README.md)" ] || bad "I1 topic '$t' first row is $first (want README.md)"
done

if printf '%s\n' "$ROWS" | grep -q '_(none yet' && ls -d "$R"/*/ >/dev/null 2>&1; then
  bad "I1 placeholder row still present although topics exist"
fi

# ---- I9: run scratch must not outlive the run -------------------------------
# `.wip/` is a checkpoint for session-death recovery, not corpus content. It holds
# raw subagent returns, which are by definition not yet verified — step 6 is where
# citations get checked and contradicted claims deleted. Anything still in `.wip/`
# either never passed that pass or was thrown away by it.
echo "I9  no run scratch left behind"
while IFS= read -r d; do
  [ -n "$d" ] || continue
  bad "I9 ${d#"$R"/} survived the run — delete .wip/ on completion (it is pre-verification scratch, not corpus)"
done <<EOF
$(find "$R" -type d -name '.wip' 2>/dev/null | sort)
EOF

echo "---"
[ "$fail" -eq 0 ] && echo "PASS  $R" || echo "FAIL  $R"
exit "$fail"

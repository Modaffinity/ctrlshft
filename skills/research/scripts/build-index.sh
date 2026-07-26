#!/usr/bin/env bash
set -euo pipefail

mode="write"
if [ "${1:-}" = "--stdout" ]; then
  mode="stdout"
  shift
fi

R="${1:-context/research}"
R="${R%/}"
[ -f "$R/INDEX.md" ] || { echo "FATAL: no INDEX.md in $R" >&2; exit 1; }

cell_list() {
  sed -E 's/^[^:]+:[[:space:]]*//; s/^\[//; s/\]$//; s/,[[:space:]]*/, /g'
}

frontmatter() {
  awk 'NR>1 && /^---$/{exit} NR>1' "$1"
}

field() {
  local file="$1" key="$2" value
  value="$(frontmatter "$file" | sed -nE "s/^$key:[[:space:]]*(.*)\$/\1/p" | head -1)"
  value="${value%\"}"
  value="${value#\"}"
  printf '%s' "$value"
}

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

{
  awk '/^\| Topic \| Doc \| Serves task\(s\) \| Tags \| Status \| Summary \|/{exit} {print}' "$R/INDEX.md"
  printf '| Topic | Doc | Serves task(s) | Tags | Status | Summary |\n'
  printf '|---|---|---|---|---|---|\n'

  find "$R" -mindepth 2 -maxdepth 2 -type f -name '*.md' |
    awk -v base="$R/" '
      {
        rel=$0; sub("^" base, "", rel)
        n=split(rel, p, "/")
        topic=p[1]; file=p[n]
        rank=(file=="README.md" ? "000000" : file)
        print topic "\t" rank "\t" rel "\t" $0
      }' |
    sort -t "$(printf '\t')" -k1,1 -k2,2 |
    while IFS="$(printf '\t')" read -r topic _ rel file; do
      tasks="$(frontmatter "$file" | sed -nE '/^tasks:/p' | cell_list)"
      tags="$(frontmatter "$file" | sed -nE '/^tags:/p' | cell_list)"
      status="$(field "$file" status)"
      summary="$(field "$file" summary)"
      doc="$(basename "$file")"
      printf '| %s | [%s](%s) | %s | %s | %s | %s |\n' \
        "$topic" "$doc" "$rel" "$tasks" "$tags" "$status" "$summary"
    done

  awk '
    /^\| Topic \| Doc \| Serves task\(s\) \| Tags \| Status \| Summary \|/ { in_table=1; next }
    in_table && /^\|/ { next }
    in_table && /^$/ { pending_blank=1; next }
    in_table {
      if (pending_blank) print ""
      print
      while (getline) print
      exit
    }' "$R/INDEX.md"
} > "$tmp"

if [ "$mode" = "stdout" ]; then
  cat "$tmp"
else
  cp "$tmp" "$R/INDEX.md"
fi

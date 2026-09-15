#!/usr/bin/env bash
# M10 — C16, the operator's gate at the plan freeze (SPEC.md § 12).
#
#   b6-gate.sh <plan path>
#
# Reads the plan's frontmatter `approved:` and opens B6 ONLY when the value parses as an
# ISO date `YYYY-MM-DD`. Anything else — `pending`, empty, absent, or any other string —
# is a refusal. Exit 0 opens, exit 1 refuses, exit 2 is a usage error and never a verdict:
# a gate that cannot read its plan has not approved it, and saying so on stderr keeps the
# two outcomes distinguishable from the one line on stdout.
#
# **This gate has no waiver branch (R155).** A literal waiver value baked in here would
# weaken the mechanism for every future run to accommodate one. A run that must open B6
# without an approval does it as an OVERRIDE recorded in `STATE.md`'s ledger — the gate
# runs, refuses, and the refusal is what the ruling overrides. An override visible in the
# ledger is the shape CHECKS.md rule 2 asks for; a waiver branch in the code is the shape
# it forbids.
#
# This file is the SINGLE implementation of the date test and the single source of the
# refusal string. `dispatch-gate.py` (M10b) shells out to it rather than re-parsing the
# frontmatter, so the hook and the CLI can never drift into two answers.
#
# Frontmatter is parsed as frontmatter, never grepped: a plan whose prose quotes
# `approved: 2026-09-20` has not been approved.
set -uo pipefail

REFUSED='b6-gate: plan not approved (approved: %s) — B6 does not open.\n'
OPENED='b6-gate: approved (%s) — B6 opens.\n'

usage() {
    printf 'b6-gate: %s\nusage: b6-gate.sh <plan path>\n' "$1" >&2
    exit 2
}

trim() {
    local s=$1
    s=${s#"${s%%[![:space:]]*}"}
    s=${s%"${s##*[![:space:]]}"}
    printf '%s' "$s"
}

# The frontmatter value of `approved:`, or the empty string with status 1 when the plan
# carries no leading `---` block or no such key. The FIRST occurrence wins.
approved_value() {
    local path=$1 line key value
    {
        IFS= read -r line || return 1
        [ "${line%$'\r'}" = "---" ] || return 1
        while IFS= read -r line; do
            line=${line%$'\r'}
            [ "$line" = "---" ] && return 1
            case "$line" in
                *:*) ;;
                *) continue ;;
            esac
            key=$(trim "${line%%:*}")
            [ "$key" = "approved" ] || continue
            value=$(trim "${line#*:}")
            # A YAML-quoted value is the same value: `"2026-09-20"` is a date.
            if [ ${#value} -ge 2 ]; then
                head=${value:0:1}
                tail=${value:${#value}-1:1}
                if [ "$head" = "$tail" ] && [ "$head" = '"' -o "$head" = "'" ]; then
                    value=${value:1:${#value}-2}
                fi
            fi
            printf '%s' "$value"
            return 0
        done
    } < "$path"
    return 1
}

# `YYYY-MM-DD`, read by the calendar rather than by shape: `2026-13-01` and `2026-02-30`
# are date-shaped and are not dates.
is_iso_date() {
    local value=$1 year month day last
    [[ $value =~ ^([0-9]{4})-([0-9]{2})-([0-9]{2})$ ]] || return 1
    year=$((10#${BASH_REMATCH[1]}))
    month=$((10#${BASH_REMATCH[2]}))
    day=$((10#${BASH_REMATCH[3]}))
    (( month >= 1 && month <= 12 )) || return 1
    last=31
    case $month in
        4|6|9|11) last=30 ;;
        2) last=28
           (( (year % 4 == 0 && year % 100 != 0) || year % 400 == 0 )) && last=29 ;;
    esac
    (( day >= 1 && day <= last ))
}

[ $# -eq 1 ] || usage "expected exactly one argument, got $#"
PLAN=$1
[ -f "$PLAN" ] && [ -r "$PLAN" ] || usage "cannot read $PLAN"

if VALUE=$(approved_value "$PLAN"); then
    if is_iso_date "$VALUE"; then
        # shellcheck disable=SC2059
        printf "$OPENED" "$VALUE"
        exit 0
    fi
else
    VALUE='<absent>'
fi
# shellcheck disable=SC2059
printf "$REFUSED" "$VALUE"
exit 1

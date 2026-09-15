#!/usr/bin/env bash
# codex-run.sh — M13. Logging, never containment.
#
#   codex-run.sh --label <task id> -- <codex args>
#
# Runs the Codex CLI at its resolved absolute path, files
# evidence/codex-run-<ts>-<label>/{cmd.txt,stdout.txt,stderr.txt,meta.json}
# in the current repository, and re-emits Codex's stdout unchanged with its
# exit code.
#
# This wrapper adds no sandbox, refuses no read and is NOT a fence.
# Containment is `default_permissions = "plan-release-3"` in ~/.codex/config.toml,
# which both the plugin path and this one inherit with no flag and no memory.
#
# Exit codes: Codex's own, or 3 usage, 4 environment.

set -uo pipefail

usage() {
	cat >&2 <<'USAGE'
usage: codex-run.sh [--label <task id>] -- <codex args...>

  --label <task id>  the task this dispatch belongs to (T12, T13, ...). Recorded
                     verbatim as meta.json's `task` so a route can be joined to
                     the seat actually used. Omitted, `task` is null and the run
                     reports as an unattributed Codex dispatch rather than a guess.
  --                 required separator. Everything after it is passed to Codex
                     verbatim; this wrapper adds nothing and removes nothing.

Environment:
  CODEX_BIN                  override the binary (default: `command -v codex`,
                             else /Applications/ChatGPT.app/Contents/Resources/codex)
  CODEX_RUN_EVIDENCE_ROOT    override the repository root the evidence dir is
                             written under (default: the enclosing git work tree,
                             else $PWD)
USAGE
}

die_usage() {
	printf 'codex-run.sh: %s\n\n' "$1" >&2
	usage
	exit 3
}

label=""
have_separator=0

while [ "$#" -gt 0 ]; do
	case "$1" in
	--)
		have_separator=1
		shift
		break
		;;
	--label)
		[ "$#" -ge 2 ] || die_usage "--label needs a task id"
		label="$2"
		shift 2
		;;
	--label=*)
		label="${1#--label=}"
		shift
		;;
	-h | --help)
		usage
		exit 3
		;;
	*)
		die_usage "unknown option before the -- separator: $1"
		;;
	esac
done

[ "$have_separator" -eq 1 ] || die_usage "missing the -- separator before the codex arguments"
[ "$#" -ge 1 ] || die_usage "no codex arguments after the -- separator"

case "$label" in
*/* | *[[:space:]]*)
	die_usage "label must be a bare task id with no path separator or whitespace: $label"
	;;
esac

CODEX_BIN="${CODEX_BIN:-$(command -v codex || echo /Applications/ChatGPT.app/Contents/Resources/codex)}"
if [ ! -x "$CODEX_BIN" ]; then
	printf 'codex-run.sh: codex binary is not executable: %s\n' "$CODEX_BIN" >&2
	exit 4
fi

codex_argv=("$@")

# Observe the seat from the argv actually sent — never inject it, never assume a
# default. Absent, meta.json records null and T7's --routes reports the dispatch
# as unattributed rather than guessing which model answered.
model=""
effort=""
i=0
while [ "$i" -lt "${#codex_argv[@]}" ]; do
	arg="${codex_argv[$i]}"
	next=""
	[ $((i + 1)) -lt "${#codex_argv[@]}" ] && next="${codex_argv[$((i + 1))]}"
	case "$arg" in
	--model | -m) model="$next" ;;
	--model=*) model="${arg#--model=}" ;;
	-c | --config)
		case "$next" in
		model_reasoning_effort=*) effort="${next#model_reasoning_effort=}" ;;
		esac
		;;
	--config=model_reasoning_effort=*) effort="${arg#--config=model_reasoning_effort=}" ;;
	-cmodel_reasoning_effort=*) effort="${arg#-cmodel_reasoning_effort=}" ;;
	esac
	i=$((i + 1))
done
# strip one layer of shell-surviving quotes, e.g. -c 'model_reasoning_effort="high"'
model="${model%\"}"
model="${model#\"}"
effort="${effort%\"}"
effort="${effort#\"}"

root="${CODEX_RUN_EVIDENCE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
stamp="$(date -u +%Y%m%d-%H%M%SZ)"
dir="$root/evidence/codex-run-$stamp-${label:-unlabeled}"
mkdir -p "$dir" || {
	printf 'codex-run.sh: cannot create evidence directory: %s\n' "$dir" >&2
	exit 4
}

{
	printf '%s\n' "$CODEX_BIN"
	for arg in "${codex_argv[@]}"; do printf '%s\n' "$arg"; done
} >"$dir/cmd.txt"

started="$(date -u +%s)"
"$CODEX_BIN" "${codex_argv[@]}" >"$dir/stdout.txt" 2>"$dir/stderr.txt"
code="$?"
duration="$(($(date -u +%s) - started))"

json_string() {
	if [ -z "$1" ]; then
		printf 'null'
	else
		printf '"%s"' "$(printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
	fi
}

{
	printf '{\n'
	printf '  "task": %s,\n' "$(json_string "$label")"
	printf '  "model": %s,\n' "$(json_string "$model")"
	printf '  "effort": %s,\n' "$(json_string "$effort")"
	printf '  "exit": %d,\n' "$code"
	printf '  "duration": %d,\n' "$duration"
	printf '  "stamp": "%s",\n' "$stamp"
	printf '  "binary": %s\n' "$(json_string "$CODEX_BIN")"
	printf '}\n'
} >"$dir/meta.json"

# Re-emit Codex's stdout unchanged, and hand back its own exit code.
cat "$dir/stdout.txt"
printf 'codex-run.sh: evidence %s\n' "$dir" >&2
exit "$code"

#!/usr/bin/env python3
"""AC20 — every mechanism of SPEC.md § 19 resolves, and every hook of it is live in BOTH
settings files with the right matcher and the right command.

Event names alone are not a check (X8). Comparing `sorted(hooks.keys())` between the two
files passes untouched when an unrelated command is wired under an existing event name,
and the whole of C12 rests on this one criterion. This asserts exact
`(event, matcher, command)` triples instead, against `hook-inventory.json`.

    check-hook-wiring.py --expect <inventory> --settings <path> --mirror <path>

Exit 0 all present · 1 naming every triple missing, mismatched in matcher or command, or
present in one file and not the other (R151) · 2 an input did not parse.

Stdlib only, Python 3.9.
"""
import argparse
import json
import os
import subprocess
import sys

OK, BAD = "✓", "✗"
PENDING = "⧖"


def die(message):
    sys.stdout.write("%s\n" % message)
    raise SystemExit(2)


def load(path, label):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        die("%s did not parse: %s" % (label, exc))


def triples(doc):
    """Every (event, matcher, command) a settings document actually wires. A group with
    no `matcher` key applies to everything, which is the inventory's `*`."""
    found = set()
    for event, groups in (doc.get("hooks") or {}).items():
        for group in groups or []:
            matcher = group.get("matcher") or "*"
            for entry in group.get("hooks") or []:
                if "command" in entry:
                    found.add((event, matcher, entry["command"]))
    return found


def status_line(doc):
    value = doc.get("statusLine")
    if isinstance(value, dict):
        return value.get("command")
    return value


def matchers_for(found, event, command):
    return sorted(m for (e, m, c) in found if e == event and c == command)


def resolve_pod(given):
    if given:
        return os.path.abspath(os.path.expanduser(given))
    env = os.environ.get("PLAN_POD")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True)
    except OSError:
        return None
    return out.stdout.strip() or None


def expand(raw, roots):
    path = raw
    for token, value in roots.items():
        if token in path:
            if value is None:
                return None, path
            path = path.replace(token, value)
    return os.path.expanduser(path), path


def check_hook(row, settings, mirror, out):
    event, matcher, command = row["event"], row.get("matcher") or "*", row["command"]
    want = (event, matcher, command)
    in_settings, in_mirror = want in settings, want in mirror
    note = ""
    if not (in_settings and in_mirror):
        seen = set(matchers_for(settings, event, command)
                   + matchers_for(mirror, event, command)) - {matcher}
        if seen:
            note = "  (command is wired under matcher %s)" % ", ".join(sorted(seen))
    out.append("%s %s %s %s settings %s mirror%s"
               % (event, matcher, command,
                  OK if in_settings else BAD, OK if in_mirror else BAD, note))
    return in_settings and in_mirror


def check_statusline(row, settings, mirror, out):
    command = row["command"]
    in_settings = status_line(settings) == command
    in_mirror = status_line(mirror) == command
    out.append("statusLine — %s %s settings %s mirror"
               % (command, OK if in_settings else BAD, OK if in_mirror else BAD))
    return in_settings and in_mirror


def check_path(row, roots, allow_pending, out):
    raw = row["path"]
    entries = raw if isinstance(raw, list) else [raw]
    lands = row.get("lands")
    ok = True
    for item in entries:
        path, shown = expand(item, roots)
        if path is None:
            out.append("%s %s %s %s unresolved placeholder"
                       % (row["mechanism"], row.get("executor", "?"), shown, BAD))
            ok = False
            continue
        exists = os.path.exists(path)
        if lands and not exists and allow_pending:
            out.append("%s %s %s %s pending %s"
                       % (row["mechanism"], row.get("executor", "?"), path,
                          PENDING, lands))
            continue
        if lands and exists and allow_pending:
            # The flag is not a permanent excuse: once the deliverable lands, the row
            # must be de-flagged or it would stop being checked for the rest of the run.
            out.append("%s %s %s %s stale pending %s — remove `lands` from the "
                       "inventory row" % (row["mechanism"], row.get("executor", "?"),
                                          path, BAD, lands))
            ok = False
            continue
        out.append("%s %s %s %s on disk"
                   % (row["mechanism"], row.get("executor", "?"), path,
                      OK if exists else BAD))
        ok = ok and exists
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect", required=True)
    parser.add_argument("--settings", required=True)
    parser.add_argument("--mirror", required=True)
    parser.add_argument("--pod", default=None,
                        help="root for <pod> paths; default git toplevel of cwd")
    parser.add_argument("--allow-pending", action="store_true",
                        help="a `path` row carrying `lands` may be absent until that "
                             "task ships it; strict by default, and the release-end "
                             "AC20 run passes no flag")
    args = parser.parse_args(argv)

    inventory = load(args.expect, "inventory")
    settings_doc = load(args.settings, "settings")
    mirror_doc = load(args.mirror, "mirror")

    settings, mirror = triples(settings_doc), triples(mirror_doc)
    roots = {
        "<dotfiles>": os.path.expanduser("~/dotfiles"),
        "<pkg>": os.path.expanduser("~/dotfiles/skills/plan"),
        "<pod>": resolve_pod(args.pod),
    }

    out, failures = [], 0
    for row in inventory.get("rows") or []:
        kind = row.get("kind")
        if kind == "hook":
            passed = check_hook(row, settings, mirror, out)
        elif kind == "statusline":
            passed = check_statusline(row, settings_doc, mirror_doc, out)
        elif kind == "path":
            passed = check_path(row, roots, args.allow_pending, out)
        else:
            out.append("unknown inventory kind %r" % kind)
            passed = False
        failures += 0 if passed else 1

    sys.stdout.write("\n".join(out) + "\n")
    total = len(inventory.get("rows") or [])
    sys.stdout.write("RESULT: %d of %d inventory rows resolved\n"
                     % (total - failures, total))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

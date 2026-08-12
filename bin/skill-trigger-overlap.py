#!/usr/bin/env python3
"""skill-trigger-overlap.py — report skills competing for the same trigger words.

    python3 ~/dotfiles/bin/skill-trigger-overlap.py

Exit: ALWAYS 0. This reports; it never fails.

WHY THIS EXISTS (OL-109). Every skill in the co-load set enters the same Claude Code
session, and the model chooses between them using only each skill's `description`.
Nothing arbitrates. When two claim the same words one silently never fires, and the
failure is misread as "that skill is broken" rather than "it never ran".

WHY IT NEVER FAILS. A check that fails on a quoted phrase is silenced by deleting the
quotes: the overlap survives, coverage drops, the tool goes green. It would reward
making the estate less legible. Judgement about which skill should own a word is the
operator's, not a gate's.

WHY THE POPULATION IS NARROW. It is what actually LOADS. Scanning ~/.claude/plugins
directly reports 78 skills and 10 overlapping pairs; resolving enabledPlugins first
reports 51 and 3. The extra seven name skills that never load — unactionable findings
are exactly the noise that gets a report ignored.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()

# Every input is overridable so the fixture never reads the real estate.
SKILLS_ROOT = Path(os.environ.get("SKILLS_ROOT") or HOME / "dotfiles" / "skills")
PLUGINS_ROOT = Path(os.environ.get("PLUGINS_ROOT") or HOME / ".claude" / "plugins")

if os.environ.get("SETTINGS_FILES"):
    SETTINGS_FILES = [Path(p) for p in os.environ["SETTINGS_FILES"].split(os.pathsep) if p]
else:
    SETTINGS_FILES = [
        HOME / ".claude" / "settings.json",
        HOME / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "settings.json",
        Path.cwd() / ".claude" / "settings.local.json",
    ]

# States that remove a skill from the listing the model routes on.
HIDDEN_STATES = {"off", "user-invocable-only"}

# Two rules, and BOTH were found by testing rather than reasoning.
#
# 1. A quote opens a run only when the preceding character is not alphanumeric, and
#    closes one only when the following character is not alphanumeric. Without this,
#    every possessive and contraction opens a phantom phrase that swallows prose to
#    the next apostrophe — and phantom phrases overlap with each other, filling the
#    report with punctuation.
#
# 2. The body may not contain the delimiter. Without this, a length floor of 3 makes
#    the match RUN PAST a too-short item to the next quote: "Use 'a' or 'ab' or
#    'abc'." yields the phantom phrase "a or ab", which no skill ever claimed.
QUOTED = re.compile(r"""(?<![A-Za-z0-9])(['"])((?:(?!\1).){3,60})\1(?![A-Za-z0-9])""", re.S)


def load_settings(paths):
    """Merge enabledPlugins and skillOverrides across the settings layers.

    Later files win, matching Claude Code's own layering. Unreadable or invalid
    files are skipped rather than fatal: a broken project-local settings file
    must not stop the report.
    """
    enabled, overrides = {}, {}
    for path in paths:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        enabled.update(data.get("enabledPlugins") or {})
        overrides.update(data.get("skillOverrides") or {})
    return enabled, overrides


def frontmatter_description(path):
    """Return the description value, continuation lines joined, outer quotes stripped."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    match = re.search(r"^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", parts[1], re.S | re.M)
    if not match:
        return ""
    value = " ".join(match.group(1).split())
    # Strip ONE wrapping quote pair. Most descriptions are written
    # description: "… 'audit' …", and a short fully-quoted one would otherwise be
    # extracted as a single enormous trigger phrase.
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def normalise(text):
    """Compare on meaning, not typography: casing must not defeat the check."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def phrases(description):
    """The trigger phrases a description CLAIMS, normalised.

    Only quoted runs count. Roughly two thirds of the estate declares triggers in
    prose instead and is invisible here — which is why the coverage line is
    printed on every run and why this reports rather than validates.
    """
    found = set()
    for _quote, body in QUOTED.findall(description):
        normalised = normalise(body)
        if len(normalised) >= 3:
            found.add(normalised)
    return found


def discover(skills_root, plugins_root, enabled, overrides):
    """Return (loaded, silenced). Only `loaded` can compete for a trigger."""
    loaded, silenced = [], []

    def add(name, source, path, editable):
        # skillOverrides does NOT affect plugin skills (they are managed through
        # /plugin), so an override may only silence an editable dotfiles skill.
        state = overrides.get(name, "on") if editable else "on"
        record = {
            "name": name,
            "source": source,
            "path": Path(path),
            "description": frontmatter_description(path),
            "editable": editable,
        }
        (silenced if state in HIDDEN_STATES else loaded).append(record)

    for skill_md in sorted(Path(skills_root).glob("*/SKILL.md")):
        add(skill_md.parent.name, "dotfiles", skill_md, True)
    for skill_md in sorted((Path(skills_root) / "_local").glob("*/SKILL.md")):
        add(skill_md.parent.name, "dotfiles/_local", skill_md, True)

    for key, on in sorted(enabled.items()):
        if not on:
            continue
        plugin, _, marketplace = key.partition("@")
        root = Path(plugins_root) / "cache" / marketplace / plugin
        # The version directory varies; marketplaces/ holds a second copy of the
        # same plugin and is deliberately not scanned.
        for skill_md in sorted(root.glob("*/skills/*/SKILL.md")):
            add(skill_md.parent.name, f"plugin {key}", skill_md, False)

    return loaded, silenced


def render_sources(loaded, silenced):
    """Name what was resolved, so a smaller-than-expected population is visible."""
    lines = ["  Sources resolved:"]
    counts = {}
    for record in loaded:
        counts[record["source"]] = counts.get(record["source"], 0) + 1
    for source in sorted(counts):
        lines.append(f"    {source:<44}{counts[source]} skill(s)")
    if silenced:
        names = ", ".join(sorted(r["name"] for r in silenced))
        lines.append(f"    {'silenced by skillOverrides (excluded)':<44}{len(silenced)}: {names}")
    return lines


def main():
    enabled, overrides = load_settings(SETTINGS_FILES)
    loaded, silenced = discover(SKILLS_ROOT, PLUGINS_ROOT, enabled, overrides)

    print("Skill trigger overlap — the co-loading set is the population")
    print()

    if not loaded:
        # LOUD FAILURE BEATS SILENT ZERO. A stale root scans nothing, finds no
        # overlap and prints a clean result while measuring nothing.
        print(f"  NOTHING WAS MEASURED — no skills found under {SKILLS_ROOT}")
        print("  This is not a clean result. Check the path before believing it.")
        return 0

    print(f"  {len(loaded)} skill(s) co-loading")
    print()
    for line in render_sources(loaded, silenced):
        print(line)

    analysable = [record for record in loaded if phrases(record["description"])]
    print()
    print(f"  {len(analysable)} of {len(loaded)} analysable "
          f"· {len(loaded) - len(analysable)} declare triggers in prose and cannot be checked")
    print("  A skill can also fail to fire because its description was dropped for")
    print("  context budget — run /doctor for that; this tool cannot see it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

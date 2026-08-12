"""Unit tests for bin/skill-trigger-overlap.py.

Builds throwaway skill trees in tempfile, points the tool at them with
SKILLS_ROOT / PLUGINS_ROOT / SETTINGS_FILES, and asserts on stdout.
Never reads ~/dotfiles/skills or ~/.claude.

Run: python3 -m unittest discover -s test/python -p "test_*.py" -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "bin" / "skill-trigger-overlap.py"


class Fixture(unittest.TestCase):
    """Builds a throwaway estate and runs the tool against it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skilltrig."))
        self.skills = self.tmp / "skills"
        self.plugins = self.tmp / "plugins"
        self.settings = self.tmp / "settings.json"
        self.skills.mkdir(parents=True)
        self.write_settings({})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_settings(self, data):
        self.settings.write_text(json.dumps(data), encoding="utf-8")

    def add_skill(self, name, description, plugin=None):
        """plugin=None puts it in the dotfiles tree; otherwise 'name@marketplace'."""
        if plugin is None:
            d = self.skills / name
        else:
            pname, _, market = plugin.partition("@")
            d = self.plugins / "cache" / market / pname / "1.0.0" / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
            encoding="utf-8",
        )

    def run_tool(self):
        env = dict(os.environ)
        env["SKILLS_ROOT"] = str(self.skills)
        env["PLUGINS_ROOT"] = str(self.plugins)
        env["SETTINGS_FILES"] = str(self.settings)
        proc = subprocess.run(
            [sys.executable, str(TOOL)],
            capture_output=True, text=True, env=env,
        )
        return proc


class TestPopulation(Fixture):
    def test_dotfiles_skills_are_in_the_population(self):
        self.add_skill("alpha", '"Does alpha."')
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1 skill", proc.stdout)

    def test_disabled_plugin_skills_are_excluded(self):
        self.add_skill("alpha", '"Does alpha."')
        self.add_skill("beta", '"Does beta."', plugin="ghostplug@mkt")
        # ghostplug is NOT in enabledPlugins
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        # A skill name alone only reaches stdout inside a finding, so asserting on
        # "beta" is vacuous here (there is no finding to carry it). Assert on the
        # population count and the source name instead — both would change if the
        # disabled plugin's skill were wrongly included.
        self.assertIn("1 skill(s) co-loading", proc.stdout)
        self.assertNotIn("ghostplug", proc.stdout)

    def test_enabled_plugin_skills_are_included(self):
        self.add_skill("alpha", '"Does alpha."')
        self.add_skill("beta", '"Does beta."', plugin="realplug@mkt")
        self.write_settings({"enabledPlugins": {"realplug@mkt": True}})
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("realplug@mkt", proc.stdout)

    def test_silenced_dotfiles_skill_leaves_the_population(self):
        self.add_skill("alpha", '"Does alpha."')
        self.add_skill("quiet", '"Does quiet things."')
        self.write_settings({"skillOverrides": {"quiet": "user-invocable-only"}})
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("silenced", proc.stdout)

    def test_skill_overrides_do_not_silence_plugin_skills(self):
        """Documented Claude Code behaviour: plugin skills ignore skillOverrides."""
        self.add_skill("shared", '"Plugin copy."', plugin="realplug@mkt")
        self.write_settings({
            "enabledPlugins": {"realplug@mkt": True},
            "skillOverrides": {"shared": "off"},
        })
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("realplug@mkt", proc.stdout)

    def test_stale_plugin_version_directory_does_not_double_count(self):
        """A plugin update can leave a stale version directory behind. Only the
        newest should load; scanning both gives two records an identical _key,
        which either reports a skill as conflicting with itself or lets the
        second silently overwrite the first in overlaps() (finding 3)."""
        self.add_skill("alpha", '"Does alpha."')
        for version in ("1.0.0", "2.0.0"):
            d = self.plugins / "cache" / "mkt" / "realplug" / version / "skills" / "dup"
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text(
                '---\nname: dup\ndescription: "Does dup."\n---\n\n# dup\n',
                encoding="utf-8",
            )
        self.write_settings({"enabledPlugins": {"realplug@mkt": True}})
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        # One "dup" record only: alpha (dotfiles) + dup (newest plugin version).
        self.assertIn("2 skill(s) co-loading", proc.stdout)
        routing_block = proc.stdout.split("OVERLAP CANDIDATES")[0]
        self.assertIn("(none)", routing_block)
        self.assertNotIn(
            "plugin realplug@mkt:dup  <->  plugin realplug@mkt:dup", proc.stdout
        )

    def test_all_silenced_reports_override_not_path(self):
        """If every discovered skill is silenced, the path is not the problem —
        skillOverrides is. The 'nothing measured' message must say so instead of
        blaming SKILLS_ROOT (finding 4)."""
        self.add_skill("quiet", '"Does quiet things."')
        self.write_settings({"skillOverrides": {"quiet": "off"}})
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("nothing was measured", proc.stdout.lower())
        self.assertIn("skilloverrides", proc.stdout.lower())
        self.assertIn("quiet", proc.stdout)

    def test_missing_root_reports_nothing_measured_not_clean(self):
        shutil.rmtree(self.skills)
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("nothing was measured", proc.stdout.lower())

    def test_empty_root_reports_nothing_measured_not_clean(self):
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("nothing was measured", proc.stdout.lower())

    def test_settings_of_unexpected_top_level_shape_does_not_crash(self):
        """A settings file that parses as valid JSON but is not an object (e.g. a
        bare list) must be skipped like any other unreadable file, not crash
        load_settings() before the first print."""
        self.add_skill("alpha", '"Does alpha."')
        self.settings.write_text("[]", encoding="utf-8")
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1 skill", proc.stdout)

    def test_settings_field_of_unexpected_shape_does_not_crash(self):
        """enabledPlugins/skillOverrides are expected to be objects; a settings file
        that declares one as some other JSON type must not crash the merge."""
        self.add_skill("alpha", '"Does alpha."')
        self.write_settings({"enabledPlugins": ["a@b"]})
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1 skill", proc.stdout)


class TestPhraseExtraction(Fixture):
    def test_coverage_line_counts_analysable_skills(self):
        self.add_skill("quoted", """ "Does things. Use when asked to 'do a thing'." """)
        self.add_skill("prose", '"Use when encountering any bug or test failure."')
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1 of 2 analysable", proc.stdout)

    def test_possessives_and_contractions_raise_no_phantom_phrase(self):
        # Without the alphanumeric-boundary rule, each apostrophe opens a run that
        # swallows prose to the next one, and phantom runs collide with each other.
        self.add_skill("gamma", '"Reads the agent\'s config and the user\'s prefs; don\'t guess."')
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0 of 1 analysable", proc.stdout)

    def test_wholly_quoted_short_description_is_not_a_trigger(self):
        self.add_skill("delta", '"Fix the widget"')
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0 of 1 analysable", proc.stdout)

    def test_short_quoted_items_do_not_span_into_a_phantom_phrase(self):
        """A length floor without a delimiter exclusion runs PAST a short item.

        'Use "a" or "ab" or "abc".' must yield only "abc" — never "a or ab",
        which no skill claimed. Found by testing the primitive before building on
        it; the naive pattern produced exactly that phantom.
        """
        self.add_skill("epsilon", """ "Use 'a' or 'ab' or 'abcdef' here." """)
        self.add_skill("zeta", """ "Also 'a' or 'ab' but nothing else." """)
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        # zeta claims nothing >= 3 chars, so it cannot be analysable and the two
        # cannot overlap on a phantom.
        self.assertIn("1 of 2 analysable", proc.stdout)
        self.assertIn("no overlap", proc.stdout.lower())


class TestDetection(Fixture):
    def test_same_name_different_descriptions_is_a_naming_note_not_a_duplicate(self):
        """Plugin skills are namespaced, so a shared name is not a routing conflict."""
        self.add_skill("shared", '"Ours does one thing."')
        self.add_skill("shared", '"Theirs does another thing."', plugin="realplug@mkt")
        self.write_settings({"enabledPlugins": {"realplug@mkt": True}})
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("NAMING NOTES", proc.stdout)
        # It must NOT be presented as a routing duplicate.
        routing_block = proc.stdout.split("NAMING NOTES")[0]
        self.assertIn("(none)", routing_block)

    def test_identical_description_is_a_routing_duplicate(self):
        self.add_skill("alpha", '"Use when encountering any bug."')
        self.add_skill("beta", '"Use when encountering any bug."')
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        routing_block = proc.stdout.split("OVERLAP CANDIDATES")[0]
        self.assertIn("dotfiles:alpha", routing_block)
        self.assertIn("dotfiles:beta", routing_block)

    def test_containment_is_caught_not_only_equality(self):
        self.add_skill("wide", """ "Use when asked to 'code review'." """)
        self.add_skill("narrow", """ "Use when asked to 'do a code review'." """)
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("code review", proc.stdout)

    def test_a_phrase_only_one_skill_quotes_is_not_an_overlap(self):
        self.add_skill("alpha", """ "Use when asked to 'run the thing'." """)
        self.add_skill("beta", """ "Use when asked to 'something else entirely'." """)
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("no overlap", proc.stdout.lower())

    def test_prose_only_skills_do_not_overlap_each_other(self):
        self.add_skill("alpha", '"Use when encountering any bug."')
        self.add_skill("beta", '"Use when reviewing changes."')
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("no overlap", proc.stdout.lower())

    def test_uneditable_side_is_marked(self):
        """Identical descriptions, so this is a ROUTING duplicate and gets the marker."""
        self.add_skill("shared", '"Use when encountering any bug."')
        self.add_skill("shared", '"Use when encountering any bug."', plugin="realplug@mkt")
        self.write_settings({"enabledPlugins": {"realplug@mkt": True}})
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("cannot be edited", proc.stdout.lower())

    def test_overlap_uneditable_side_is_named(self):
        """The overlap section must NAME the side skillOverrides cannot reach, the
        same way the routing-duplicates section already does (finding 6). This is
        a phrase overlap, not an identical description, so it renders in OVERLAP
        CANDIDATES rather than ROUTING DUPLICATES.

        The pair header line always names both sides, so asserting on the header
        alone would pass even with the old generic "one side cannot be edited"
        note — pin the exact note line instead, or this test is as vacuous as the
        one finding 2 replaced."""
        self.add_skill("wide", """ "Use when asked to 'code review'." """)
        self.add_skill(
            "narrow", """ "Use when asked to 'do a code review'." """,
            plugin="realplug@mkt",
        )
        self.write_settings({"enabledPlugins": {"realplug@mkt": True}})
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn(
            "plugin realplug@mkt:narrow cannot be edited — silence yours instead",
            proc.stdout,
        )
        self.assertNotIn("one side cannot be edited", proc.stdout)

    def test_overlap_neither_side_editable_gets_accurate_note(self):
        """When BOTH sides of an overlap are plugin skills, 'silence yours instead'
        is wrong — there is no 'yours' to silence into. A different, accurate line
        is required (finding 5)."""
        self.add_skill(
            "wide", """ "Use when asked to 'code review'." """,
            plugin="pluginone@mkt",
        )
        self.add_skill(
            "narrow", """ "Use when asked to 'do a code review'." """,
            plugin="plugintwo@mkt",
        )
        self.write_settings({
            "enabledPlugins": {"pluginone@mkt": True, "plugintwo@mkt": True},
        })
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        overlap_block = proc.stdout.split("OVERLAP CANDIDATES")[1]
        self.assertNotIn("silence yours instead", overlap_block)
        self.assertIn("plugin pluginone@mkt:wide", overlap_block)
        self.assertIn("plugin plugintwo@mkt:narrow", overlap_block)

    def test_silencing_one_side_clears_the_finding(self):
        """A resolved finding must stay resolved, or the report gets ignored.

        This is the real systematic-debugging case: identical descriptions, one
        side a plugin we cannot edit, resolved by silencing ours.
        """
        self.add_skill("shared", '"Use when encountering any bug."')
        self.add_skill("shared", '"Use when encountering any bug."', plugin="realplug@mkt")
        self.write_settings({
            "enabledPlugins": {"realplug@mkt": True},
            "skillOverrides": {"shared": "user-invocable-only"},
        })
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        routing_block = proc.stdout.split("OVERLAP CANDIDATES")[0]
        self.assertIn("(none)", routing_block)
        self.assertNotIn("NAMING NOTES", proc.stdout)


if __name__ == "__main__":
    unittest.main()

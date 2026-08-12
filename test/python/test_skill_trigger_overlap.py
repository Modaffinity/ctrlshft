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
        self.assertNotIn("beta", proc.stdout)

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

    def test_missing_root_reports_nothing_measured_not_clean(self):
        shutil.rmtree(self.skills)
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("nothing was measured", proc.stdout.lower())

    def test_empty_root_reports_nothing_measured_not_clean(self):
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("nothing was measured", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()

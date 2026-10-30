"""The Claude Code plugin wiring: manifest, marketplace, hooks, launcher and skills."""

import json
import os
import re
import subprocess
import sys
import unittest

from agency_os import __version__

from helpers import ROOT, TEMPLATE, TempDir, copy_tree


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


class ManifestTest(unittest.TestCase):
    def test_plugin_manifest(self):
        data = load(".claude-plugin/plugin.json")
        self.assertEqual(data["name"], "agency-os")
        self.assertEqual(data["version"], __version__)
        self.assertRegex(data["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_marketplace_lists_the_plugin_at_root(self):
        data = load(".claude-plugin/marketplace.json")
        self.assertEqual([p["source"] for p in data["plugins"]], ["./"])
        self.assertIn("name", data["owner"])


class HooksTest(unittest.TestCase):
    def test_events_and_commands(self):
        hooks = load("hooks/hooks.json")["hooks"]
        self.assertEqual(set(hooks), {"SessionStart", "Stop", "PreCompact"})
        commands = [h["command"] for groups in hooks.values() for g in groups for h in g["hooks"]]
        for cmd in commands:
            self.assertIn('"${CLAUDE_PLUGIN_ROOT}/scripts/agency-os"', cmd)
        subcommands = sorted(c.split('"')[2].split()[0] for c in commands)
        self.assertEqual(subcommands, ["checkpoint", "context", "session-log"])

    def run_launcher(self, args, stdin):
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=ROOT, NO_COLOR="1")
        env.pop("AGENCY_OS_VAULT", None)
        return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "agency-os")] + args,
                              input=stdin, capture_output=True, universal_newlines=True, env=env, timeout=60)

    def test_launcher_runs_each_hook_like_claude_code_does(self):
        with TempDir() as d:
            copy_tree(TEMPLATE, os.path.join(d, "vault"))
            transcript = os.path.join(ROOT, "tests", "fixtures", "transcript.jsonl")
            base = {"session_id": "abcdef12", "cwd": d, "transcript_path": transcript}
            start = self.run_launcher(["context", "--hook"], json.dumps(dict(base, hook_event_name="SessionStart", source="startup")))
            self.assertEqual(start.returncode, 0, start.stderr)
            self.assertIn("company memory", start.stdout)
            stop = self.run_launcher(["session-log", "--person", "ci"], json.dumps(dict(base, hook_event_name="Stop")))
            self.assertEqual((stop.returncode, stop.stdout), (0, ""), stop.stderr)
            pre = self.run_launcher(["checkpoint", "--person", "ci"], json.dumps(dict(base, hook_event_name="PreCompact", trigger="manual")))
            self.assertEqual((pre.returncode, pre.stdout), (0, ""), pre.stderr)
            sessions = os.listdir(os.path.join(d, "vault", "08 - Sessions"))
            self.assertTrue(any(s.endswith("Sessions, ci.md") for s in sessions))
            self.assertTrue(os.listdir(os.path.join(d, "vault", "08 - Sessions", "Checkpoints")))


class SkillsTest(unittest.TestCase):
    def test_skill_frontmatter(self):
        skills_dir = os.path.join(ROOT, "skills")
        names = sorted(os.listdir(skills_dir))
        self.assertEqual(names, ["capture", "open-loops", "vault-health"])
        for name in names:
            with open(os.path.join(skills_dir, name, "SKILL.md"), encoding="utf-8") as fh:
                text = fh.read()
            fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
            self.assertIsNotNone(fm, name)
            self.assertIn("name: {}\n".format(name), fm.group(1) + "\n")
            self.assertRegex(fm.group(1), r"description: .{40,}")
            self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/agency-os", text)


if __name__ == "__main__":
    unittest.main()

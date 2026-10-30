import json
import os
import unittest

from agency_os import index
from agency_os.lint import lint
from agency_os.scaffold import ScaffoldError, init
from agency_os.vault import Vault

from helpers import TempDir, run_cli


def walk_text(root):
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith((".md", ".json")):
                with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                    yield os.path.join(dirpath, f), fh.read()


class InitTest(unittest.TestCase):
    def test_with_examples_is_lint_clean_and_renamed(self):
        with TempDir() as d:
            init(d, "Acme Agency", today="2026-10-30")
            vault = Vault(os.path.join(d, "vault"))
            self.assertEqual([f.as_dict() for f in lint(vault).findings], [])
            self.assertIn("01 - Company/Acme Agency.md", vault.notes)
            self.assertEqual(vault.config["company_hub"], "Acme Agency")
            for path, text in walk_text(d):
                self.assertNotIn("Northwind Studio", text, path)
            self.assertTrue(index.is_current(vault))

    def test_without_examples_is_lint_clean_and_empty_of_fiction(self):
        with TempDir() as d:
            init(d, "Blue Fox Media", vault_dir="brain", examples=False, today="2026-10-30")
            root = os.path.join(d, "brain")
            vault = Vault(root)
            self.assertEqual([f.as_dict() for f in lint(vault).findings], [])
            self.assertFalse([n.rel for n in vault.knowledge_notes() if "example" in n.tags])
            for fiction in ("Acme Bakery", "Bluebird", "Cobalt Legal", "Jonas", "Weekly Team Meeting"):
                for path, text in walk_text(root):
                    if "/07 - Templates/" in path.replace(os.sep, "/"):
                        continue
                    self.assertNotIn(fiction, text, path)
            # Emptied folders survive a git commit, and tables keep their header for new rows.
            self.assertTrue(os.path.exists(os.path.join(root, "08 - Sessions", ".gitkeep")))
            register = vault.notes["01 - Company/Open Loops Register.md"].text
            self.assertIn("| Loop | Owner | Opened | Due | Where |", register)

    def test_claude_md_and_autopilot_are_rendered(self):
        with TempDir() as d:
            init(d, "Acme Agency", vault_dir="memory", today="2026-10-30")
            with open(os.path.join(d, "CLAUDE.md"), encoding="utf-8") as fh:
                claude = fh.read()
            with open(os.path.join(d, "vault-autopilot.md"), encoding="utf-8") as fh:
                autopilot = fh.read()
            self.assertIn("# Acme Agency: operating instructions", claude)
            self.assertIn("`memory/01 - Company/Vault Guide for Claude Code Sessions.md`", claude)
            self.assertIn("update the\n> fact in place", claude)
            self.assertNotIn("{{", claude + autopilot)

    def test_refuses_to_overwrite_without_force(self):
        with TempDir() as d:
            init(d, "Acme Agency")
            with self.assertRaises(ScaffoldError):
                init(d, "Acme Agency")
            with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as fh:
                fh.write("my edits")
            init(d, "Acme Agency", force=True)
            with self.assertRaises(ScaffoldError):
                init(d, "Acme Agency", vault_dir="../escape")

    def test_existing_claude_md_is_kept(self):
        with TempDir() as d:
            with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as fh:
                fh.write("ours")
            init(d, "Acme Agency")
            with open(os.path.join(d, "CLAUDE.md"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "ours")

    def test_hooks_settings_are_merged_once(self):
        with TempDir() as d:
            os.makedirs(os.path.join(d, ".claude"))
            with open(os.path.join(d, ".claude", "settings.json"), "w", encoding="utf-8") as fh:
                json.dump({"permissions": {"allow": ["Bash(ls)"]}}, fh)
            init(d, "Acme Agency", hooks=True)
            init(d, "Acme Agency", hooks=True, force=True)
            with open(os.path.join(d, ".claude", "settings.json"), encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["permissions"], {"allow": ["Bash(ls)"]})
            self.assertEqual(len(data["hooks"]["Stop"]), 1)
            self.assertEqual(set(data["hooks"]), {"SessionStart", "Stop", "PreCompact"})

    def test_cli(self):
        with TempDir() as d:
            code, out, _ = run_cli("init", d, "--name", "Acme Agency", "--no-examples")
            self.assertEqual(code, 0)
            self.assertIn("lint clean", out)
            code, _, err = run_cli("init", d, "--name", "Acme Agency")
            self.assertEqual(code, 2)
            self.assertIn("--force", err)


if __name__ == "__main__":
    unittest.main()

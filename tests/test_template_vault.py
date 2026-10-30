import json
import os
import unittest

from agency_os import index
from agency_os.lint import lint
from agency_os.vault import Vault

from helpers import TEMPLATE, run_cli


class TemplateVaultTest(unittest.TestCase):
    """The shipped template vault is the reference: it must stay spotless."""

    @classmethod
    def setUpClass(cls):
        cls.vault = Vault(TEMPLATE)

    def test_lint_has_no_findings_at_all(self):
        result = lint(self.vault)
        self.assertEqual([f.as_dict() for f in result.findings], [])

    def test_cli_strict_passes(self):
        code, out, _ = run_cli("lint", TEMPLATE, "--strict")
        self.assertEqual(code, 0, out)
        self.assertIn("clean", out)

    def test_index_is_current(self):
        self.assertTrue(index.is_current(self.vault), "run: agency-os index template-vault")

    def test_every_note_has_a_summary(self):
        missing = [n.rel for n in self.vault.knowledge_notes() if not n.summary()]
        self.assertEqual(missing, [])

    def test_folder_skeleton(self):
        folders = sorted(d for d in os.listdir(TEMPLATE) if not d.startswith(".") and os.path.isdir(os.path.join(TEMPLATE, d)))
        self.assertEqual(folders, [
            "00 - Home", "01 - Company", "02 - Clients", "03 - Projects", "04 - Knowledge Base",
            "05 - Meetings", "06 - Resources", "07 - Templates", "08 - Sessions", "99 - Archive",
        ])

    def test_all_templates_present(self):
        names = sorted(os.listdir(os.path.join(TEMPLATE, "07 - Templates")))
        self.assertEqual(names, [
            "Client.md", "Decision Record.md", "Meeting.md", "Open Loop.md",
            "Project.md", "SOP.md", "Session Log.md",
        ])

    def test_configured_entry_points_exist(self):
        cfg = self.vault.config
        for key in ("home", "index", "guide", "open_loops"):
            self.assertIn(cfg[key], self.vault.notes, key)
        for hub in cfg["hubs"] + [cfg["company_hub"]]:
            self.assertIsNotNone(self.vault.note_named(hub), hub)

    def test_obsidian_config_is_valid_json(self):
        obs = os.path.join(TEMPLATE, ".obsidian")
        for name in os.listdir(obs):
            if name.endswith(".json"):
                with open(os.path.join(obs, name), encoding="utf-8") as fh:
                    json.load(fh)
        with open(os.path.join(obs, "appearance.json"), encoding="utf-8") as fh:
            snippets = json.load(fh)["enabledCssSnippets"]
        for s in snippets:
            self.assertTrue(os.path.exists(os.path.join(obs, "snippets", s + ".css")))


if __name__ == "__main__":
    unittest.main()

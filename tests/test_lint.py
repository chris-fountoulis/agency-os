import json
import os
import unittest

from agency_os.lint import lint
from agency_os.vault import Vault

from helpers import FIXTURES, TempDir, note, run_cli, write

BROKEN = os.path.join(FIXTURES, "broken-vault")


def findings(vault_path, **kw):
    return {(f.check, f.note) for f in lint(Vault(vault_path), **kw).findings}


class PlantedErrorsTest(unittest.TestCase):
    """Every planted defect in tests/fixtures/broken-vault is found, and nothing else."""

    @classmethod
    def setUpClass(cls):
        cls.result = lint(Vault(BROKEN))
        cls.found = {(f.check, f.note) for f in cls.result.findings}

    def assertFound(self, check, rel):
        self.assertIn((check, rel), self.found, "expected {} on {}".format(check, rel))

    def test_broken_link(self):
        self.assertFound("broken-link", "02 - Clients/Client A.md")
        msgs = [f.message for f in self.result.findings if f.check == "broken-link"]
        self.assertEqual(len(msgs), 1, "inline code links must be ignored")
        self.assertIn("Missing Project", msgs[0])

    def test_orphans(self):
        self.assertFound("orphan", "02 - Clients/Client B.md")
        self.assertFound("orphan", "04 - Knowledge Base/Loose Thoughts.md")

    def test_hub_links(self):
        self.assertFound("no-hub", "02 - Clients/Client B.md")
        self.assertFound("no-hub", "04 - Knowledge Base/Empty Procedure.md")

    def test_empty_note(self):
        self.assertFound("empty", "04 - Knowledge Base/Empty Procedure.md")

    def test_empty_archive_note_is_allowed(self):
        self.assertNotIn(("empty", "99 - Archive/Old Plan.md"), self.found)

    def test_generic_name(self):
        self.assertFound("generic-name", "02 - Clients/Untitled.md")

    def test_frontmatter(self):
        msgs = {(f.note, f.message) for f in self.result.findings if f.check == "frontmatter"}
        self.assertIn(("02 - Clients/Untitled.md", "missing 'status'"), msgs)
        self.assertIn(("02 - Clients/Untitled.md", "date '01/10/2026' is not YYYY-MM-DD"), msgs)
        self.assertIn(("02 - Clients/Client B.md", "type 'customer' is not in the vocabulary"), msgs)
        self.assertIn(("04 - Knowledge Base/Loose Thoughts.md", "no frontmatter block"), msgs)

    def test_status_optional_for_navigation_notes(self):
        self.assertNotIn(("frontmatter", "00 - Home/Home.md"), self.found)
        self.assertNotIn(("frontmatter", "01 - Company/Sales.md"), self.found)

    def test_duplicate_names(self):
        self.assertFound("duplicate-title", "02 - Clients/Shared Name.md")
        self.assertFound("duplicate-title", "04 - Knowledge Base/Shared Name.md")

    def test_moc_membership(self):
        self.assertFound("moc", "02 - Clients/Client B.md")
        self.assertFound("moc", "04 - Knowledge Base/Loose Thoughts.md")
        self.assertNotIn(("moc", "02 - Clients/Client A.md"), self.found)

    def test_templates_are_not_linted(self):
        self.assertFalse(any(rel.startswith("07 - Templates") for _, rel in self.found))

    def test_exact_counts(self):
        self.assertEqual(len(self.result.errors), 11)
        self.assertEqual(len(self.result.warnings), 5)

    def test_ignore(self):
        found = findings(BROKEN, ignore={"orphan", "moc"})
        self.assertFalse(any(c in ("orphan", "moc") for c, _ in found))


class DashCheckTest(unittest.TestCase):
    def test_dash_only_when_enabled(self):
        with TempDir() as d:
            write(d, "01 - Company/Sales.md", note({"tags": ["hub"], "type": "hub", "date": "2026-10-01"},
                                                   "# Sales\n\nThe sales hub, see [[Pricing]]."))
            body = "# Pricing\n\n[[Sales]]\n\nRates \u2014 per month.\n\n```\ncode \u2014 ok\n```"
            write(d, "04 - Knowledge Base/Pricing.md", note(
                {"tags": ["sop"], "type": "sop", "status": "active", "date": "2026-10-01"}, body))
            self.assertNotIn("dash", {c for c, _ in findings(d)})
            write(d, "agency-os.json", '{"forbid_dashes": true}')
            dash = [f for f in lint(Vault(d)).findings if f.check == "dash"]
            self.assertEqual([f.line for f in dash], [12])


class LinkResolutionTest(unittest.TestCase):
    def test_aliases_headings_paths_and_attachments(self):
        with TempDir() as d:
            fm = {"tags": ["x"], "type": "sop", "status": "active", "date": "2026-10-01"}
            write(d, "01 - Company/Sales.md", note({"tags": ["hub"], "type": "hub", "date": "2026-10-01"},
                                                   "# Sales\n\n[[A]] [[B]]"))
            write(d, "04 - Knowledge Base/A.md", note(fm, "# A\n\n[[Sales|the sales hub]] [[B#Part]] "
                                                      "[[04 - Knowledge Base/B]] ![[logo.png]] [[b]]"))
            write(d, "04 - Knowledge Base/B.md", note(fm, "# B\n\n[[Sales]] [[A#^block1]]"))
            write(d, "assets/logo.png", "png")
            found = findings(d, ignore={"moc"})
            self.assertNotIn("broken-link", {c for c, _ in found})


class CliTest(unittest.TestCase):
    def test_exit_codes(self):
        code, out, _ = run_cli("lint", BROKEN)
        self.assertEqual(code, 1)
        self.assertIn("11 errors, 5 warnings", out)
        code, _, err = run_cli("lint", os.path.join(FIXTURES, "does-not-exist"))
        self.assertEqual(code, 2)
        self.assertIn("vault not found", err)
        code, _, err = run_cli("lint", BROKEN, "--ignore", "nonsense")
        self.assertEqual(code, 2)

    def test_warnings_only_pass_unless_strict(self):
        with TempDir() as d:
            write(d, "01 - Company/Sales.md", note({"tags": ["hub"], "type": "hub", "date": "2026-10-01"},
                                                   "# Sales\n\nHub."))
            write(d, "04 - Knowledge Base/Lonely.md", note(
                {"tags": ["sop"], "type": "sop", "status": "active", "date": "2026-10-01"},
                "# Lonely\n\n[[Sales]] only."))
            self.assertEqual(run_cli("lint", d, "--ignore", "moc")[0], 0)
            self.assertEqual(run_cli("lint", d, "--ignore", "moc", "--strict")[0], 1)

    def test_json_output(self):
        code, out, _ = run_cli("lint", BROKEN, "--format", "json")
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(data["errors"], 11)
        self.assertEqual(data["notes"], 15)
        self.assertEqual(set(data["findings"][0]), {"check", "severity", "note", "line", "message"})

    def test_bad_config_is_usage_error(self):
        with TempDir() as d:
            write(d, "agency-os.json", '{"hubz": []}')
            code, _, err = run_cli("lint", d)
            self.assertEqual(code, 2)
            self.assertIn("unknown key", err)


if __name__ == "__main__":
    unittest.main()

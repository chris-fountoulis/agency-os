import json
import os
import unittest

from agency_os.lint import lint
from agency_os.spinout import SpinoutError, spinout, verify
from agency_os.vault import Vault

from helpers import TEMPLATE, TempDir, copy_tree, run_cli


def all_text(root):
    chunks = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            with open(os.path.join(dirpath, f), encoding="utf-8", errors="replace") as fh:
                chunks.append(fh.read())
    return "\n".join(chunks)


class SpinoutTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.tmp = self._tmp.__enter__()
        self.src = copy_tree(TEMPLATE, os.path.join(self.tmp, "src"))
        # Plant things that must never leave the studio.
        path = os.path.join(self.src, "02 - Clients", "Acme Bakery.md")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\nOur INTERNAL MARGIN here is high. Bluebird referred them. Ask Lena.\n"
                     "Old booking key: " + "sk-" + "live0" * 6 + "\n"
                     "Codename Project Lighthouse is internal.\n")
        self.denyfile = os.path.join(self.tmp, "deny.txt")
        with open(self.denyfile, "w", encoding="utf-8") as fh:
            fh.write("# team names\nLena\n\nProject Lighthouse\n")

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def run_spinout(self, **kw):
        out = os.path.join(self.tmp, "acme")
        return out, spinout(self.src, "Acme Bakery", out, denylist_files=[self.denyfile], today="2026-10-30", **kw)

    def test_scrubs_every_denylist_source(self):
        out, report = self.run_spinout(deny=["WhatsApp"])
        text = all_text(out)
        for term in ("internal margin", "Bluebird", "Cobalt", "Lena", "Project Lighthouse", "WhatsApp"):
            self.assertNotIn(term.lower(), text.lower(), term)
        self.assertEqual(report["leak_details"], [])
        sources = {t["source"] for t in report["terms"] if t["replacements"]}
        self.assertEqual(sources, {"config", "file", "cli", "other-client"})

    def test_redacts_credentials(self):
        out, report = self.run_spinout()
        self.assertNotIn("live0live0", all_text(out))
        self.assertEqual(report["notes_with_secrets_redacted"], 1)

    def test_selection_and_exclusions(self):
        out, report = self.run_spinout()
        self.assertEqual(report["notes"], [
            "02 - Clients/Acme Bakery.md",
            "03 - Projects/Acme Bakery Website Relaunch.md",
            "04 - Knowledge Base/Playbook, Instagram Content Calendar.md",
            "04 - Knowledge Base/SOP, Client Onboarding.md",
            "05 - Meetings/2026-10-20 Acme Bakery Kickoff.md",
        ])
        deeper = spinout(self.src, "Acme Bakery", os.path.join(self.tmp, "deep"), depth=2)
        self.assertIn("04 - Knowledge Base/SOP, Monthly Client Report.md", deeper["notes"])
        for rel in deeper["notes"]:
            self.assertFalse(rel.startswith(("08 - Sessions", "01 - Company/Open Loops", "01 - Company/Team")), rel)

    def test_output_is_a_lint_clean_vault(self):
        out, _ = self.run_spinout()
        vault = Vault(out)
        self.assertEqual([f.as_dict() for f in lint(vault).findings], [])
        self.assertIn("00 - Home/Home.md", vault.notes)
        self.assertIn("00 - Home/All Notes Index.md", vault.notes)
        with open(os.path.join(out, "agency-os.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
        self.assertNotIn("spinout", cfg, "the source denylist must not travel")

    def test_report_file_never_names_terms(self):
        out, report = self.run_spinout()
        with open(os.path.join(out, ".agency-os", "spinout-report.json"), encoding="utf-8") as fh:
            raw = fh.read()
        for t in report["terms"]:
            self.assertNotIn(t["term"].lower(), raw.lower())
        self.assertEqual(json.loads(raw)["leaks"], 0)

    def test_verify_catches_leaks(self):
        out, _ = self.run_spinout()
        with open(os.path.join(out, "02 - Clients", "Acme Bakery.md"), "a", encoding="utf-8") as fh:
            fh.write("\nCobalt slipped in.\n")
        leaks = verify(out, ["Cobalt"])
        self.assertEqual(leaks, [("02 - Clients/Acme Bakery.md", "term: Cobalt")])

    def test_refuses_bad_targets(self):
        with self.assertRaises(SpinoutError):
            spinout(self.src, "Nobody Inc", os.path.join(self.tmp, "x"))
        with self.assertRaises(SpinoutError):
            spinout(self.src, "Acme Bakery", os.path.join(self.src, "inside"))
        with self.assertRaises(SpinoutError):
            spinout(self.src, "SOP, Client Onboarding", os.path.join(self.tmp, "y"))
        out, _ = self.run_spinout()
        with self.assertRaises(SpinoutError):
            spinout(self.src, "Acme Bakery", out)

    def test_cli(self):
        out = os.path.join(self.tmp, "cli-out")
        code, stdout, _ = run_cli("spinout", self.src, "--client", "Acme Bakery", "--out", out,
                                  "--denylist", self.denyfile)
        self.assertEqual(code, 0, stdout)
        self.assertIn("verified: no denylisted term", stdout)
        code, _, err = run_cli("spinout", self.src, "--client", "Nobody", "--out", out + "2")
        self.assertEqual(code, 2)
        self.assertIn("Clients: Acme Bakery, Bluebird Fitness, Cobalt Legal", err)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from agency_os import stats
from agency_os.loops import open_loops
from agency_os.vault import Vault

from helpers import TEMPLATE, run_cli


class StatsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = stats.compute(Vault(TEMPLATE))

    def test_index_is_not_counted(self):
        names = [m["note"] for m in self.data["most_linked"]]
        self.assertNotIn("All Notes Index", names)
        self.assertEqual(self.data["notes"], sum(self.data["by_folder"].values()))
        self.assertNotIn("index", self.data["by_type"])

    def test_template_vault_is_fully_connected(self):
        self.assertEqual(self.data["orphan_rate"], 0.0)
        self.assertEqual(self.data["hub_coverage"], 100.0)
        self.assertEqual(self.data["broken_links"], 0)
        self.assertGreater(self.data["link_density"], 3)

    def test_activity(self):
        self.assertEqual(self.data["session_logs"], 2)
        self.assertEqual(self.data["session_entries"], 2)
        self.assertEqual(self.data["latest_session"], "2026-10-28")

    def test_cli_text_and_json(self):
        code, out, _ = run_cli("stats", TEMPLATE)
        self.assertEqual(code, 0)
        self.assertIn("Link density", out)
        self.assertIn("Northwind Studio", out)
        code, out, _ = run_cli("stats", TEMPLATE, "--format", "json")
        self.assertEqual(json.loads(out)["open_loops"], 4)


class LoopsTest(unittest.TestCase):
    def test_open_rows_only(self):
        loops = open_loops(Vault(TEMPLATE), today="2026-10-30")
        self.assertEqual(len(loops), 4)
        self.assertTrue(all("kickoff call booked" not in l["loop"].lower() for l in loops))
        first = loops[0]
        self.assertEqual(first["owner"], "Lena")
        self.assertEqual(first["where"], "Acme Bakery Website Relaunch")
        self.assertEqual(first["links"], ["Acme Bakery Website Relaunch"])

    def test_overdue(self):
        overdue = [l["loop"] for l in open_loops(Vault(TEMPLATE), today="2026-11-02") if l["overdue"]]
        self.assertEqual(overdue, ["Confirm the November ad budget in writing"])

    def test_cli_filters(self):
        code, out, _ = run_cli("loops", TEMPLATE, "--overdue", "--today", "2026-11-04")
        self.assertEqual(code, 0)
        self.assertIn("2 open, 2 overdue", out)
        code, out, _ = run_cli("loops", TEMPLATE, "--owner", "jonas", "--format", "json")
        self.assertEqual([l["owner"] for l in json.loads(out)], ["Jonas"])


if __name__ == "__main__":
    unittest.main()

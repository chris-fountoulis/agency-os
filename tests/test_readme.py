"""The README demo blocks are real output; this keeps them that way."""

import os
import unittest

from helpers import FIXTURES, ROOT, TEMPLATE, run_cli


def readme():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


class ReadmeDemoTest(unittest.TestCase):
    def assertInReadme(self, output):
        output = output.rstrip("\n").replace(TEMPLATE, "template-vault").replace(
            os.path.join(FIXTURES, "broken-vault"), "tests/fixtures/broken-vault")
        self.assertIn(output, readme(), "README demo is stale; paste the new output")

    def test_stats_block(self):
        _, out, _ = run_cli("stats", TEMPLATE)
        self.assertInReadme(out.replace("agency-os stats  " + TEMPLATE, "agency-os stats  template-vault"))

    def test_lint_blocks(self):
        self.assertInReadme(run_cli("lint", TEMPLATE)[1])
        self.assertInReadme(run_cli("lint", os.path.join(FIXTURES, "broken-vault"))[1])

    def test_quickstart_mentions_real_commands(self):
        text = readme()
        for cmd in ("init my-agency", "/plugin marketplace add chris-fountoulis/agency-os",
                    "/plugin install agency-os@agency-os"):
            self.assertIn(cmd, text)


if __name__ == "__main__":
    unittest.main()

"""House rules for the repository itself."""

import os
import stat
import unittest

from helpers import ROOT

SKIP_DIRS = {".git", "__pycache__", "build", "dist", ".venv", "venv", "node_modules"}
TEXT_EXT = {".py", ".md", ".json", ".yml", ".yaml", ".toml", ".sh", ".css", ".cff", ".txt", ".template",
            ".service", ".timer", ".jsonl", ""}


def text_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        for f in filenames:
            if os.path.splitext(f)[1] in TEXT_EXT:
                yield os.path.join(dirpath, f)


class HygieneTest(unittest.TestCase):
    def test_no_em_or_en_dashes_anywhere(self):
        bad = []
        for path in text_files():
            with open(path, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    if "\u2014" in line or "\u2013" in line:
                        bad.append("{}:{}".format(os.path.relpath(path, ROOT), n))
        self.assertEqual(bad, [], "use a comma, a period, a colon or a hyphen")

    def test_executables(self):
        for rel in ("scripts/agency-os", "sync/vault-sync.sh", "sync/install.sh"):
            path = os.path.join(ROOT, rel)
            with open(path, encoding="utf-8") as fh:
                self.assertTrue(fh.readline().startswith("#!"), rel)
            if os.name != "nt":
                self.assertTrue(os.stat(path).st_mode & stat.S_IXUSR, rel + " is not executable")


if __name__ == "__main__":
    unittest.main()

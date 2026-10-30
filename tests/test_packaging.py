"""pip installs copy template-vault/ and templates/ via [tool.setuptools.data-files].

That list is explicit (setuptools data-files does not recurse), so this test
fails the moment a note is added to the template vault without being listed.
"""

import os
import re
import unittest

from helpers import ROOT


def listed_files():
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as fh:
        text = fh.read()
    section = text.split("[tool.setuptools.data-files]", 1)[1]
    files = set()
    for line in section.splitlines():
        m = re.match(r'^"([^"]+)" = \[(.*)\]$', line.strip())
        if m:
            for src in re.findall(r'"([^"]+)"', m.group(2)):
                self_dir = "share/agency-os/" + os.path.dirname(src)
                assert m.group(1) == self_dir, (m.group(1), src)
                files.add(src)
    return files


def files_on_disk(folder):
    found = set()
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, folder)):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in filenames:
            if f in ("workspace.json", ".DS_Store"):
                continue
            found.add(os.path.relpath(os.path.join(dirpath, f), ROOT).replace(os.sep, "/"))
    return found


class PackagingTest(unittest.TestCase):
    def test_data_files_match_disk(self):
        expected = files_on_disk("template-vault") | files_on_disk("templates")
        self.assertEqual(sorted(listed_files() ^ expected), [],
                         "update [tool.setuptools.data-files] in pyproject.toml")


if __name__ == "__main__":
    unittest.main()

import os
import unittest

from agency_os import __version__

from helpers import TEMPLATE, TempDir, run_cli


class CliBasicsTest(unittest.TestCase):
    def test_no_command_prints_help_and_exits_2(self):
        code, out, _ = run_cli()
        self.assertEqual(code, 2)
        self.assertIn("lint", out)
        self.assertIn("spinout", out)

    def test_version(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli("--version")
        self.assertEqual(ctx.exception.code, 0)

    def test_every_command_has_help(self):
        for cmd in ("init", "lint", "index", "stats", "loops", "spinout", "session-log", "checkpoint", "context"):
            with self.assertRaises(SystemExit) as ctx:
                run_cli(cmd, "--help")
            self.assertEqual(ctx.exception.code, 0, cmd)

    def test_vault_is_found_from_a_subfolder(self):
        cwd = os.getcwd()
        try:
            os.chdir(os.path.join(TEMPLATE, "02 - Clients"))
            code, out, _ = run_cli("lint", "--quiet")
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0)
        self.assertIn("35 notes", out)

    def test_no_vault_anywhere_is_a_usage_error(self):
        with TempDir() as d:
            cwd = os.getcwd()
            try:
                os.chdir(d)
                code, _, err = run_cli("stats")
            finally:
                os.chdir(cwd)
        self.assertEqual(code, 2)
        self.assertIn("no vault found", err)

    def test_index_check_detects_a_stale_index(self):
        import shutil
        with TempDir() as d:
            vault = shutil.copytree(TEMPLATE, os.path.join(d, "v"))
            self.assertEqual(run_cli("index", vault, "--check")[0], 0)
            with open(os.path.join(vault, "06 - Resources", "Glossary.md"), "a", encoding="utf-8") as fh:
                fh.write("\nOne more line.\n")
            path = os.path.join(vault, "06 - Resources", "Glossary.md")
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace("Words we use with clients", "Terms we use with clients"))
            self.assertEqual(run_cli("index", vault, "--check")[0], 1)
            code, out, _ = run_cli("index", vault)
            self.assertIn("written", out)
            self.assertEqual(run_cli("index", vault, "--check")[0], 0)


if __name__ == "__main__":
    unittest.main()

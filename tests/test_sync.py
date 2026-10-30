"""sync/vault-sync.sh against a real bare remote and two clones."""

import os
import shutil
import subprocess
import unittest

from helpers import ROOT, TempDir

SCRIPT = os.path.join(ROOT, "sync", "vault-sync.sh")
HAVE_TOOLS = bool(shutil.which("bash") and shutil.which("git"))


def git(cwd, *args):
    return subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, universal_newlines=True,
                          check=True).stdout.strip()


@unittest.skipUnless(HAVE_TOOLS, "needs bash and git")
class SyncTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TempDir()
        self.tmp = self._tmp.__enter__()
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.env = dict(os.environ, HOME=self.home, AGENCY_OS_SYNC_QUIET="0", AGENCY_OS_SYNC_MAX_BYTES="2000",
                        GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.com",
                        GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.com",
                        GIT_CONFIG_GLOBAL=os.path.join(self.tmp, "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
                        TMPDIR=self.tmp)
        with open(self.env["GIT_CONFIG_GLOBAL"], "w") as fh:
            fh.write("[init]\n\tdefaultBranch = main\n[pull]\n\trebase = false\n")
        self.remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remote], check=True, env=self.env)
        self.a = self.clone("a")
        self.write(self.a, "00 - Home/Home.md", "# Home\n")
        self.sync(self.a)  # first run pushes the new branch

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def clone(self, name):
        path = os.path.join(self.tmp, name)
        subprocess.run(["git", "clone", "-q", self.remote, path], check=True, env=self.env,
                       capture_output=True)
        return path

    def write(self, repo, rel, text):
        path = os.path.join(repo, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def sync(self, repo):
        result = subprocess.run(["bash", SCRIPT, repo], env=self.env, capture_output=True, universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def remote_files(self):
        return git(self.remote, "ls-tree", "-r", "--name-only", "main").splitlines()

    def test_commits_and_pushes(self):
        self.write(self.a, "02 - Clients/Acme Bakery.md", "# Acme\n")
        self.sync(self.a)
        self.assertIn("02 - Clients/Acme Bakery.md", self.remote_files())
        self.assertIn("vault: sync 1 file(s)", git(self.remote, "log", "-1", "--format=%s", "main"))

    def test_holds_back_large_files_and_secrets(self):
        self.write(self.a, "big.bin", "x" * 5000)
        self.write(self.a, "leak.md", "token " + "gh" + "p_" + "Ab1" * 12 + "\n")
        self.write(self.a, "fine.md", "nothing secret here\n")
        self.sync(self.a)
        files = self.remote_files()
        self.assertIn("fine.md", files)
        self.assertNotIn("big.bin", files)
        self.assertNotIn("leak.md", files)
        status = git(self.a, "status", "--porcelain")
        self.assertIn("?? big.bin", status)
        self.assertIn("?? leak.md", status)
        with open(os.path.join(self.home, ".agency-os", "sync.log")) as fh:
            self.assertIn("held back", fh.read())

    def test_pulls_teammate_changes(self):
        b = self.clone("b")
        self.write(b, "05 - Meetings/Kickoff.md", "# Kickoff\n")
        self.sync(b)
        self.sync(self.a)
        self.assertTrue(os.path.exists(os.path.join(self.a, "05 - Meetings", "Kickoff.md")))

    def test_rebases_when_both_sides_changed(self):
        b = self.clone("b")
        self.write(b, "b.md", "from b\n")
        self.sync(b)
        self.write(self.a, "a.md", "from a\n")
        self.sync(self.a)
        files = self.remote_files()
        self.assertIn("a.md", files)
        self.assertIn("b.md", files)

    def test_pause_file(self):
        open(os.path.join(self.home, ".agency-os-sync-off"), "w").close()
        self.write(self.a, "paused.md", "x\n")
        self.sync(self.a)
        self.assertNotIn("paused.md", self.remote_files())

    def test_debounce_waits_for_quiet(self):
        env = dict(self.env, AGENCY_OS_SYNC_QUIET="3600")
        self.write(self.a, "fresh.md", "just written\n")
        subprocess.run(["bash", SCRIPT, self.a], env=env, check=True)
        self.assertNotIn("fresh.md", self.remote_files())


if __name__ == "__main__":
    unittest.main()

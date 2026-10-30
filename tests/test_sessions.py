import datetime
import json
import os
import unittest

from agency_os import sessions
from agency_os.lint import lint
from agency_os.redact import has_secret, redact
from agency_os.vault import Vault

from helpers import FIXTURES, TEMPLATE, TempDir, copy_tree, run_cli

TRANSCRIPT = os.path.join(FIXTURES, "transcript.jsonl")
NOW = datetime.datetime(2026, 10, 30, 14, 5)


def payload(**kw):
    data = {"session_id": "1a2b3c4d-0000", "transcript_path": TRANSCRIPT, "cwd": "/work/northwind",
            "hook_event_name": "Stop", "stop_hook_active": False}
    data.update(kw)
    return data


class RedactTest(unittest.TestCase):
    def test_shapes(self):
        token = "gh" + "p_" + "A1b2C3d4" * 5
        key = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
        text = "use {} and {} and https://user:pw123@example.com/x and token=Zx9-long-value".format(token, key)
        out = redact(text)
        self.assertNotIn(token, out)
        self.assertNotIn(key, out)
        self.assertNotIn("pw123", out)
        self.assertNotIn("Zx9-long-value", out)
        self.assertTrue(has_secret(text))
        self.assertFalse(has_secret(out))

    def test_plain_words_survive(self):
        text = "The password is in the vault manager. Path: 02 - Clients/Acme Bakery.md"
        self.assertEqual(redact(text), text)


class TranscriptTest(unittest.TestCase):
    def test_last_turn_files_prompt_and_reply(self):
        entries = sessions.read_transcript(TRANSCRIPT)
        turn = sessions.last_turn(entries)
        self.assertTrue(sessions.prompt_text(turn).startswith("Log the Acme kickoff"))
        self.assertEqual(sessions.files_changed(turn, "/work/northwind"), [
            "vault/05 - Meetings/2026-10-20 Acme Bakery Kickoff.md",
            "vault/05 - Meetings/Meetings MOC.md",
        ])
        self.assertIn("Logged the kickoff", sessions.last_assistant_text(turn))

    def test_missing_transcript(self):
        self.assertEqual(sessions.read_transcript("/nonexistent/x.jsonl"), [])


class SessionLogTest(unittest.TestCase):
    def test_writes_redacted_structured_entry(self):
        with TempDir() as d:
            vault = copy_tree(TEMPLATE, os.path.join(d, "vault"))
            path = sessions.session_log(payload(), vault, person="Alex Rivera", now=NOW)
            self.assertTrue(path.endswith("08 - Sessions/2026-10-30 Sessions, alex-rivera.md"))
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("written.\n\n## 14:05 · session 1a2b3c4d · northwind", text,
                          "a blank line separates the intro from the first entry")
            self.assertIn("- vault/05 - Meetings/Meetings MOC.md", text)
            self.assertNotIn("Hunter2-Bakery!9", text)
            self.assertIn("password: [REDACTED]", text)
            self.assertIn("[[Meetings MOC]]", text, "resolvable links are kept")
            self.assertNotIn("[[Nonexistent Note]]", text, "unresolvable links are unlinked")
            self.assertNotIn("Earlier prompt", text, "only the last turn is logged")
            self.assertEqual([f.as_dict() for f in lint(Vault(vault)).findings], [])

    def test_appends_and_dedupes(self):
        with TempDir() as d:
            vault = copy_tree(TEMPLATE, os.path.join(d, "vault"))
            first = sessions.session_log(payload(), vault, person="sam", now=NOW)
            self.assertIsNone(sessions.session_log(payload(), vault, person="sam", now=NOW))
            sessions.session_log(payload(last_assistant_message="A different reply."), vault, person="sam",
                                 now=NOW + datetime.timedelta(minutes=3))
            with open(first, encoding="utf-8") as fh:
                text = fh.read()
            self.assertEqual(text.count("\n## "), 2)
            self.assertEqual(text.count("# Sessions 2026-10-30, sam"), 1)

    def test_skips_subagents_and_continuations(self):
        with TempDir() as d:
            vault = copy_tree(TEMPLATE, os.path.join(d, "vault"))
            self.assertIsNone(sessions.session_log(payload(agent_id="abc"), vault, person="sam"))
            self.assertIsNone(sessions.session_log(payload(stop_hook_active=True), vault, person="sam"))

    def test_cli_never_fails(self):
        code, out, _ = run_cli("session-log", stdin="not json")
        self.assertEqual((code, out), (0, ""))
        with TempDir() as d:
            vault = copy_tree(TEMPLATE, os.path.join(d, "vault"))
            stdin = json.dumps(payload(cwd=d))
            code, out, _ = run_cli("session-log", "--person", "sam", stdin=stdin)
            self.assertEqual((code, out), (0, ""))
            logs = os.listdir(os.path.join(vault, "08 - Sessions"))
            self.assertTrue(any(name.endswith("Sessions, sam.md") for name in logs))


class CheckpointTest(unittest.TestCase):
    def test_checkpoint_note(self):
        with TempDir() as d:
            vault = copy_tree(TEMPLATE, os.path.join(d, "vault"))
            path = sessions.checkpoint(payload(hook_event_name="PreCompact", trigger="auto"), vault,
                                       person="sam", now=NOW)
            self.assertTrue(path.endswith("08 - Sessions/Checkpoints/2026-10-30 1405 Checkpoint, 1a2b3c4d.md"))
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("1. Earlier prompt about Cobalt Legal", text)
            self.assertIn("- vault/02 - Clients/Cobalt Legal.md", text)
            self.assertIn("(auto compaction)", text)
            self.assertNotIn("Hunter2-Bakery!9", text)
            self.assertEqual([f.as_dict() for f in lint(Vault(vault)).findings], [])


class ContextTest(unittest.TestCase):
    def test_briefing(self):
        text = sessions.context(TEMPLATE, today="2026-11-02")
        self.assertIn("company memory is the Obsidian vault", text)
        self.assertIn("Read first: `01 - Company/Vault Guide for Claude Code Sessions.md`", text)
        self.assertIn("Open loops: 4 open, 1 overdue", text)
        self.assertIn("- OVERDUE Confirm the November ad budget in writing (Sam, due 2026-11-01)", text)
        self.assertIn("- 2026-10-28 16:05 sam: Added a history line", text)
        self.assertIn("Vault lint: clean.", text)

    def test_hook_mode_is_silent_without_vault(self):
        with TempDir() as d:
            code, out, _ = run_cli("context", "--hook", stdin=json.dumps({"cwd": d}))
            self.assertEqual((code, out), (0, ""))

    def test_hook_mode_finds_vault_below_project(self):
        with TempDir() as d:
            copy_tree(TEMPLATE, os.path.join(d, "vault"))
            with open(os.path.join(d, "vault-autopilot.md"), "w", encoding="utf-8") as fh:
                fh.write("protocol")
            code, out, _ = run_cli("context", "--hook", stdin=json.dumps({"cwd": d, "source": "startup"}))
            self.assertEqual(code, 0)
            self.assertIn("vault at `vault`", out)
            self.assertIn("Capture protocol: `vault-autopilot.md`", out)


if __name__ == "__main__":
    unittest.main()

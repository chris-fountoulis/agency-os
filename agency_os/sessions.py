"""Claude Code hook handlers: session logs (Stop), checkpoints (PreCompact), context (SessionStart).

All three read the hook payload Claude Code sends on stdin (``session_id``,
``transcript_path``, ``cwd``, ``hook_event_name`` and, on Stop,
``last_assistant_message`` and ``stop_hook_active``). They must never get in
the way of a session: every failure is swallowed by the caller and the hook
exits 0. Session logs and checkpoints are written only after redaction.
"""

import datetime
import getpass
import hashlib
import json
import os
import re
import subprocess

from .lint import lint
from .loops import open_loops
from .redact import redact
from .vault import WIKILINK, Vault, find_vault

FILE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
TAIL_BYTES = 4 * 1024 * 1024


# -- payload and environment -------------------------------------------------

def read_payload(stream):
    try:
        data = json.load(stream)
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def locate_vault(explicit=None, payload=None):
    payload = payload or {}
    for candidate in (explicit, os.environ.get("AGENCY_OS_VAULT")):
        if candidate and os.path.isdir(candidate):
            return os.path.abspath(candidate)
    starts = [payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR")]
    if not any(starts):
        starts.append(os.getcwd())
    for start in starts:
        if start and os.path.isdir(start):
            found = find_vault(start)
            if found:
                return found
    return None


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "unknown"


def person_name(vault_root, explicit=None):
    name = explicit or os.environ.get("AGENCY_OS_PERSON")
    if not name:
        try:
            name = subprocess.run(["git", "config", "user.name"], cwd=vault_root, capture_output=True,
                                  universal_newlines=True, timeout=3).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            name = ""
    return slug(name or getpass.getuser())


# -- transcript --------------------------------------------------------------

def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _is_prompt(entry):
    """A real user turn: not a tool result, not a meta or sidechain message."""
    if entry.get("type") != "user" or entry.get("isSidechain") or entry.get("isMeta"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return False
    text = _text_of(content).strip()
    return bool(text) and not text.startswith("<command-") and not text.startswith("<local-command")


def read_transcript(path):
    """Parse the tail of a transcript JSONL file into a list of entries."""
    if not path or not os.path.isfile(path):
        return []
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size > TAIL_BYTES:
            fh.seek(size - TAIL_BYTES)
        raw = fh.read()
    lines = raw.split(b"\n")
    if size > TAIL_BYTES:
        lines = lines[1:]  # the first line is cut
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line.decode("utf-8", "replace"))
        except ValueError:
            continue
        if isinstance(obj, dict):
            entries.append(obj)
    return entries


def files_changed(entries, cwd=None):
    seen, out = set(), []
    for entry in entries:
        if entry.get("type") != "assistant" or entry.get("isSidechain"):
            continue
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            key = FILE_TOOLS.get(block.get("name"))
            path = (block.get("input") or {}).get(key) if key else None
            if not path or path in seen:
                continue
            seen.add(path)
            if cwd:
                try:
                    rel = os.path.relpath(path, cwd)
                    path = rel if not rel.startswith("..") else path
                except ValueError:
                    pass
            out.append(path.replace(os.sep, "/"))
    return out


def last_turn(entries):
    """Entries of the latest turn: from the last real prompt to the end."""
    for i in range(len(entries) - 1, -1, -1):
        if _is_prompt(entries[i]):
            return entries[i:]
    return entries


def prompt_text(entries):
    for entry in entries:
        if _is_prompt(entry):
            return _text_of(entry["message"]["content"]).strip()
    return ""


def last_assistant_text(entries):
    for entry in reversed(entries):
        if entry.get("type") == "assistant" and not entry.get("isSidechain"):
            text = _text_of((entry.get("message") or {}).get("content")).strip()
            if text:
                return text
    return ""


# -- rendering helpers -------------------------------------------------------

def clip(text, limit):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " [...]"


def quote(text):
    return "\n".join("> " + l if l.strip() else ">" for l in text.splitlines()) or ">"


def safe_links(text, vault):
    """Keep wikilinks that resolve; turn the rest into plain text so logs never break lint."""
    def fix(m):
        target = re.split(r"\\?\|", m.group(2), 1)[0].split("#", 1)[0].strip()
        if target and vault.resolve(target):
            return m.group(0)
        return re.split(r"\\?\|", m.group(2), 1)[-1]
    return WIKILINK.sub(fix, text)


def _now(now):
    return now or datetime.datetime.now()


def _write_new(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _home_name(vault):
    return os.path.basename(vault.config["home"])[:-3]


# -- Stop: session log -------------------------------------------------------

def session_log(payload, vault_root, person=None, now=None):
    """Append one entry for the turn that just ended. Returns the log path, or None if skipped."""
    if payload.get("agent_id") or payload.get("stop_hook_active"):
        return None  # a subagent's stop, or a turn a Stop hook already extended
    vault = Vault(vault_root)
    limits = vault.config["session_log"]
    cwd = payload.get("cwd") or os.getcwd()
    entries = last_turn(read_transcript(payload.get("transcript_path")))
    prompt = clip(redact(prompt_text(entries)), limits["max_prompt_chars"])
    reply = payload.get("last_assistant_message") or last_assistant_text(entries)
    summary = clip(redact(reply or ""), limits["max_reply_chars"])
    files = [redact(f) for f in files_changed(entries, cwd)][: limits["max_files"]]
    if not (prompt or summary or files):
        return None

    now = _now(now)
    sid = str(payload.get("session_id") or "nosession")[:8]
    who = person_name(vault_root, person)
    day = now.strftime("%Y-%m-%d")
    rel = "{}/{} Sessions, {}.md".format(vault.config["sessions_dir"], day, who)
    path = vault.path(rel)
    marker = "%% agency-os {} {} %%".format(sid, hashlib.sha1((prompt + summary).encode("utf-8")).hexdigest()[:10])

    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            if marker in fh.read():
                return None  # the same Stop event registered twice (plugin plus settings)
    else:
        _write_new(path, "\n".join([
            "---", "tags: [session-log]", "type: session", "status: auto", "date: {}".format(day),
            "person: {}".format(who), "---", "", "# Sessions {}, {}".format(day, who), "",
            "\u2191 [[{}]]".format(_home_name(vault)), "",
            "Written by the `agency-os session-log` Stop hook. One entry per Claude Code turn: the prompt, "
            "the files changed and the closing summary. Secrets are redacted before anything is written.", "", "",
        ]))

    block = ["## {} \u00b7 session {} \u00b7 {}".format(now.strftime("%H:%M"), sid, os.path.basename(cwd.rstrip("/\\")) or "-"),
             marker, ""]
    if prompt:
        block += ["**Prompt**", "", quote(safe_links(prompt, vault)), ""]
    if files:
        block += ["**Files changed**", ""] + ["- {}".format(f) for f in files] + [""]
    if summary:
        block += ["**Summary**", "", quote(safe_links(summary, vault)), ""]
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(block) + "\n")
    return path


# -- PreCompact: checkpoint --------------------------------------------------

def checkpoint(payload, vault_root, person=None, now=None, max_prompts=10):
    """Save what the session has done so far before the context is compacted."""
    vault = Vault(vault_root)
    cwd = payload.get("cwd") or os.getcwd()
    entries = read_transcript(payload.get("transcript_path"))
    prompts = [clip(redact(_text_of(e["message"]["content"])), 300) for e in entries if _is_prompt(e)]
    files = [redact(f) for f in files_changed(entries, cwd)]
    now = _now(now)
    sid = str(payload.get("session_id") or "nosession")[:8]
    who = person_name(vault_root, person)
    day = now.strftime("%Y-%m-%d")
    trigger = payload.get("trigger") or "unknown"
    rel = "{}/Checkpoints/{} {} Checkpoint, {}.md".format(vault.config["sessions_dir"], day, now.strftime("%H%M"), sid)
    lines = [
        "---", "tags: [checkpoint, session-log]", "type: checkpoint", "status: auto", "date: {}".format(day),
        "person: {}".format(who), "---", "",
        "# Checkpoint {} {}, session {}".format(day, now.strftime("%H:%M"), sid), "",
        "\u2191 [[{}]]".format(_home_name(vault)), "",
        "Saved by the PreCompact hook ({} compaction) so the work survives the context reset. "
        "Folder: `{}`.".format(trigger, os.path.basename(cwd.rstrip("/\\")) or "-"), "",
        "## Prompts so far", "",
    ]
    shown = prompts[-max_prompts:]
    if len(prompts) > len(shown):
        lines.append("_{} earlier prompts not shown._".format(len(prompts) - len(shown)))
        lines.append("")
    for i, p in enumerate(shown, 1):
        lines.append("{}. {}".format(i, safe_links(" ".join(p.split()), vault)))
    if not shown:
        lines.append("No prompts found in the transcript.")
    lines += ["", "## Files changed", ""]
    lines += ["- {}".format(f) for f in files] or ["None."]
    instructions = (payload.get("custom_instructions") or "").strip()
    if instructions:
        lines += ["", "## Compaction instructions", "", quote(redact(instructions))]
    path = vault.path(rel)
    _write_new(path, "\n".join(lines) + "\n")
    return path


# -- SessionStart: context ---------------------------------------------------

SESSION_HEADER = re.compile(r"^## (\d{2}:\d{2}) \u00b7 session (\S+) \u00b7 (.*)$", re.M)


def recent_entries(vault, limit=3):
    """Latest session-log entries across all people: (date, time, person, summary)."""
    found = []
    for note in vault.knowledge_notes():
        if not vault.in_dir(note.rel, "sessions_dir") or note.type != "session":
            continue
        person = note.fields.get("person") or "?"
        parts = SESSION_HEADER.split(note.body)
        # parts: [pre, time, sid, folder, body, time, sid, folder, body, ...]
        for i in range(1, len(parts) - 3, 4):
            body = parts[i + 3]
            m = re.search(r"\*\*Summary\*\*\s*\n\s*\n((?:>.*\n?)+)", body)
            text = m.group(1) if m else ""
            if not text:
                m = re.search(r"\*\*Prompt\*\*\s*\n\s*\n((?:>.*\n?)+)", body)
                text = m.group(1) if m else ""
            text = " ".join(l.lstrip("> ").strip() for l in text.splitlines()).strip()
            found.append((note.date, parts[i], person, text))
    found.sort(reverse=True)
    return found[:limit]


def context(vault_root, project_dir=None, today=None, max_loops=8):
    """The text a SessionStart hook prints: where the memory is and what is happening."""
    vault = Vault(vault_root)
    notes = [n for n in vault.knowledge_notes() if not vault.is_index(n.rel)]
    rel_root = vault.root
    if project_dir:
        rel = os.path.relpath(vault.root, project_dir)
        rel_root = vault.root if rel.startswith("..") else rel
    lines = ["agency-os: this project's company memory is the Obsidian vault at `{}` ({} notes).".format(rel_root, len(notes))]
    guide = vault.config["guide"]
    if guide in vault.notes:
        lines.append("Read first: `{}`.".format(guide))
    if project_dir and os.path.exists(os.path.join(project_dir, "vault-autopilot.md")):
        lines.append("Capture protocol: `vault-autopilot.md`. Capture decisions, facts, status changes, SOPs and open loops as they land.")
    loops = open_loops(vault, today=today)
    if loops:
        overdue = [l for l in loops if l["overdue"]]
        lines.append("")
        lines.append("Open loops: {} open, {} overdue (`{}`).".format(len(loops), len(overdue), vault.config["open_loops"]))
        ordered = overdue + [l for l in loops if not l["overdue"]]
        for l in ordered[:max_loops]:
            lines.append("- {}{} ({}, due {})".format("OVERDUE " if l["overdue"] else "", l.get("loop", "?"),
                                                     l.get("owner", "-"), l.get("due", "-")))
    recent = recent_entries(vault)
    if recent:
        lines.append("")
        lines.append("Recent sessions:")
        for day, time, person, text in recent:
            lines.append("- {} {} {}: {}".format(day, time, person, clip(text, 200) or "(no summary)"))
    result = lint(vault)
    lines.append("")
    if result.errors:
        lines.append("Vault lint: {} errors. Run `agency-os lint` and fix them before adding notes.".format(len(result.errors)))
    else:
        lines.append("Vault lint: clean.")
    return "\n".join(lines)

"""Vault configuration.

A vault is configured by an optional ``agency-os.json`` file at its root. Every
key is optional; missing keys fall back to ``DEFAULTS``. Nested dictionaries
are merged one level deep so a vault can override a single MOC or a single
spinout setting without restating the rest.
"""

import copy
import json
import os

CONFIG_NAME = "agency-os.json"

DEFAULTS = {
    # The four nodes every note must link to (directly or through its arrow line).
    "hubs": ["Management", "Product", "Sales", "Marketing"],
    # Optional company note that sits above the four hubs.
    "company_hub": "",
    "home": "00 - Home/Home.md",
    "index": "00 - Home/All Notes Index.md",
    "guide": "01 - Company/Vault Guide for Claude Code Sessions.md",
    "open_loops": "01 - Company/Open Loops Register.md",
    "clients_dir": "02 - Clients",
    "templates_dir": "07 - Templates",
    "sessions_dir": "08 - Sessions",
    "archive_dir": "99 - Archive",
    # Never scanned at all.
    "exclude_dirs": [".obsidian", ".git", ".trash", ".agency-os", "node_modules"],
    # Scanned (their links count) but exempt from the orphan and hub checks.
    "exempt_dirs": ["00 - Home", "08 - Sessions", "99 - Archive"],
    # Folder -> MOC note that must list every note in that folder.
    "mocs": {
        "02 - Clients": "02 - Clients/Clients MOC.md",
        "03 - Projects": "03 - Projects/Projects MOC.md",
        "04 - Knowledge Base": "04 - Knowledge Base/Knowledge Base MOC.md",
        "05 - Meetings": "05 - Meetings/Meetings MOC.md",
        "06 - Resources": "06 - Resources/Resources MOC.md",
    },
    "required_fields": ["tags", "type", "status", "date"],
    # Types that may omit ``status`` (navigation notes have no lifecycle).
    "status_optional_types": ["home", "hub", "moc", "index"],
    "types": [
        "home", "hub", "moc", "index", "system", "client", "project", "sop",
        "decision", "meeting", "session", "checkpoint", "open-loop", "tracker",
        "resource", "person", "concept",
    ],
    "statuses": ["active", "draft", "open", "paused", "done", "closed", "archived", "auto"],
    # Case-insensitive full-match regexes for note names nobody can find later.
    "generic_names": [
        r"untitled( \d+)?", r"notes?( \d+)?", r"misc", r"new note( \d+)?",
        r"note \d+", r"todo", r"temp", r"draft( \d+)?", r"stuff",
    ],
    # House style: flag em and en dashes in prose. Off by default.
    "forbid_dashes": False,
    "spinout": {
        # Folders whose notes may travel with a client when they are linked.
        "include_folders": ["03 - Projects", "04 - Knowledge Base", "05 - Meetings", "06 - Resources"],
        # Terms always scrubbed from a spinout, on top of other client names.
        "denylist": [],
        "replacement": "[redacted]",
    },
    "session_log": {
        "max_prompt_chars": 1200,
        "max_reply_chars": 1500,
        "max_files": 25,
    },
}


class ConfigError(Exception):
    """Raised when agency-os.json exists but cannot be used."""


def merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def load_config(vault_root):
    """Return the effective configuration for the vault at ``vault_root``."""
    path = os.path.join(vault_root, CONFIG_NAME)
    if not os.path.exists(path):
        return copy.deepcopy(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ConfigError("cannot read {}: {}".format(path, exc))
    if not isinstance(data, dict):
        raise ConfigError("{} must contain a JSON object".format(path))
    unknown = sorted(set(data) - set(DEFAULTS) - {"$schema", "name"})
    if unknown:
        raise ConfigError("{}: unknown key(s): {}".format(path, ", ".join(unknown)))
    return merge(DEFAULTS, data)

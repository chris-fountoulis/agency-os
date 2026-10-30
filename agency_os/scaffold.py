"""``agency-os init``: scaffold a vault, CLAUDE.md and the capture protocol.

The template vault ships with a fictional agency, Northwind Studio, so a new
team sees every convention in use on day one. ``init`` renames the company
everywhere. With ``examples=False`` it also removes every note tagged
``example`` and cleans up the lines that pointed at them, so the result is an
empty but fully linked, lint-clean skeleton.
"""

import datetime
import json
import os
import re
import shutil
import sys

from .vault import WIKILINK, Vault

TEMPLATE_COMPANY = "Northwind Studio"
UNSAFE_FILENAME = re.compile(r"[\\/:*?\"<>|#^\[\]]")


class ScaffoldError(Exception):
    pass


def resource_dir(name):
    """Find a bundled resource folder (``template-vault`` or ``templates``).

    Order: ``$AGENCY_OS_HOME``, the source checkout or plugin root (the
    parent of this package), then ``<prefix>/share/agency-os`` for pip installs.
    """
    candidates = []
    if os.environ.get("AGENCY_OS_HOME"):
        candidates.append(os.path.join(os.environ["AGENCY_OS_HOME"], name))
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(here, name))
    for prefix in (sys.prefix, getattr(sys, "base_prefix", sys.prefix), os.path.expanduser("~/.local")):
        candidates.append(os.path.join(prefix, "share", "agency-os", name))
    for c in candidates:
        if os.path.isdir(c):
            return c
    raise ScaffoldError("cannot find the bundled '{}' folder; set AGENCY_OS_HOME to the agency-os checkout".format(name))


def _ignore(_dir, names):
    return [n for n in names if n in ("workspace.json", "workspace-mobile.json", ".DS_Store", "__pycache__")]


def _walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for f in filenames:
            yield os.path.join(dirpath, f)


def _rename_company(root, name):
    safe = UNSAFE_FILENAME.sub("", name).strip() or "Company"
    for path in _walk_files(root):
        if path.endswith((".md", ".json")):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if TEMPLATE_COMPANY in text:
                text = text.replace("[[" + TEMPLATE_COMPANY, "[[" + safe).replace(TEMPLATE_COMPANY, name)
                if path.endswith("agency-os.json"):
                    data = json.loads(text)
                    data["company_hub"] = safe
                    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
    for path in list(_walk_files(root)):
        base = os.path.basename(path)
        if TEMPLATE_COMPANY in base:
            os.rename(path, os.path.join(os.path.dirname(path), base.replace(TEMPLATE_COMPANY, safe)))


def _drop_empty_sections(text):
    """Remove ``##`` sections left with no content after example lines were dropped.

    A table that lost all its rows keeps its header, so the team can add rows.
    """
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("## "):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("#"):
                j += 1
            if any(l.strip() for l in lines[i + 1:j]):
                out.extend(lines[i:j])
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _strip_examples(root):
    vault = Vault(root)
    removed = {n.rel for n in vault.knowledge_notes() if "example" in n.tags}
    removed_names = {vault.notes[rel].name.lower() for rel in removed}
    for rel in removed:
        os.remove(vault.path(rel))
    for rel, note in vault.notes.items():
        if rel in removed:
            continue
        changed, out = False, []
        for line in note.text.split("\n"):
            targets = [m.group(2).split("|")[0].split("#")[0].strip().rsplit("/", 1)[-1].lower()
                       for m in WIKILINK.finditer(line)]
            if not any(t in removed_names for t in targets):
                out.append(line)
                continue
            changed = True
            s = line.strip()
            if s.startswith(("- ", "* ", "|")) or re.match(r"^\d+\. ", s):
                continue  # list item or table row about an example: drop it
            out.append(WIKILINK.sub(
                lambda m: re.split(r"\\?\|", m.group(2), 1)[-1].split("#")[0]
                if m.group(2).split("|")[0].split("#")[0].strip().rsplit("/", 1)[-1].lower() in removed_names
                else m.group(0), line))
        if changed:
            text = _drop_empty_sections("\n".join(out))
            with open(vault.path(rel), "w", encoding="utf-8") as fh:
                fh.write(text)
    return sorted(removed)


def _render(path, values):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


HOOKS_SETTINGS = {
    "hooks": {
        "SessionStart": [{"hooks": [{"type": "command", "command": "agency-os context --hook", "timeout": 15}]}],
        "Stop": [{"hooks": [{"type": "command", "command": "agency-os session-log", "timeout": 15}]}],
        "PreCompact": [{"hooks": [{"type": "command", "command": "agency-os checkpoint", "timeout": 15}]}],
    }
}


def init(target, name, vault_dir="vault", examples=True, force=False, hooks=False, today=None):
    """Create the scaffold under ``target``; return a list of created paths."""
    today = today or datetime.date.today().isoformat()
    target = os.path.abspath(target)
    if os.path.isabs(vault_dir) or ".." in vault_dir.replace("\\", "/").split("/"):
        raise ScaffoldError("--vault-dir must be a relative folder name inside the target")
    dest = os.path.join(target, vault_dir)
    if os.path.exists(dest):
        if not force:
            if os.listdir(dest):
                raise ScaffoldError("{} already exists and is not empty (use --force to replace it)".format(dest))
        shutil.rmtree(dest)
    os.makedirs(target, exist_ok=True)
    shutil.copytree(resource_dir("template-vault"), dest, ignore=_ignore)
    created = [dest]

    if name != TEMPLATE_COMPANY:
        _rename_company(dest, name)
    if not examples:
        _strip_examples(dest)
        for dirpath, dirnames, filenames in os.walk(dest):
            if not dirnames and not filenames:
                open(os.path.join(dirpath, ".gitkeep"), "w").close()  # keep empty folders in git
    from .index import write_index
    write_index(Vault(dest))

    values = {"COMPANY": name, "VAULT_DIR": vault_dir.replace("\\", "/"), "DATE": today}
    templates = resource_dir("templates")
    for fname in ("CLAUDE.md", "vault-autopilot.md"):
        out = os.path.join(target, fname)
        if os.path.exists(out) and not force:
            continue
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(_render(os.path.join(templates, fname), values))
        created.append(out)

    if hooks:
        settings_dir = os.path.join(target, ".claude")
        os.makedirs(settings_dir, exist_ok=True)
        settings = os.path.join(settings_dir, "settings.json")
        data = {}
        if os.path.exists(settings):
            with open(settings, encoding="utf-8") as fh:
                data = json.load(fh)
        existing = data.setdefault("hooks", {})
        for event, entries in HOOKS_SETTINGS["hooks"].items():
            current = existing.setdefault(event, [])
            if not any("agency-os" in json.dumps(e) for e in current):
                current.extend(entries)
        with open(settings, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        created.append(settings)
    return created

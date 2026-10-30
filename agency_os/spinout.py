"""``agency-os spinout``: one client's notes as a standalone, sanitised vault.

Selection
  1. The client note, plus any notes in a folder named after the client
     (``02 - Clients/<Client>/``).
  2. Notes in ``spinout.include_folders`` that link to the client note or
     that the client note links to (its projects and meetings), skipping
     navigation notes (MOCs, hubs) and other clients.
  3. Linked knowledge: notes of ``spinout.knowledge_types`` (SOPs, resources,
     concepts) that the selection links to, followed ``depth`` levels.

Scrub, in this order
  1. Wikilinks to anything not selected become plain text.
  2. Denylisted terms are replaced: ``spinout.denylist``, ``--denylist``
     files, ``--deny`` terms, and every other client's name and aliases.
  3. Credential shapes are redacted.

Then every output file is re-scanned for each denylisted term and every
credential shape. Any survivor is a leak and fails the run. The report kept
inside the new vault counts scrubs per rule without naming the terms, so the
report itself cannot leak them.
"""

import datetime
import json
import os
import re
import shutil

from .index import write_index
from .redact import SECRET_SHAPES, redact
from .vault import WIKILINK, Vault

NAV_TYPES = {"moc", "hub", "home", "index", "session", "checkpoint", "tracker"}
UNSAFE_FILENAME = re.compile(r"[\\/:*?\"<>|#^\[\]]")


class SpinoutError(Exception):
    pass


def _names(note):
    out = [note.name]
    title = re.sub(r"^(Client|Project|Meeting):\s*", "", note.title).strip()
    if title:
        out.append(title)
    aliases = note.fields.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [a.strip() for a in aliases.split(",")]
    out.extend(a for a in aliases if a)
    return out


def read_denylist(path):
    terms = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                terms.append(line)
    return terms


def _term_pattern(term):
    edge_l = r"(?<![\w])" if term[:1].isalnum() else ""
    edge_r = r"(?![\w])" if term[-1:].isalnum() else ""
    return re.compile(edge_l + re.escape(term) + edge_r, re.I)


def _is_client(vault, note):
    return note.type == "client" or (vault.in_dir(note.rel, "clients_dir") and note.type not in NAV_TYPES
                                     and "/" not in note.rel[len(vault.config["clients_dir"]) + 1:])


def select(vault, client_note, depth=1):
    cfg = vault.config["spinout"]
    include = tuple(f + "/" for f in cfg.get("include_folders", []))
    knowledge_types = set(cfg.get("knowledge_types", ["sop", "resource", "concept"]))
    folder = "{}/{}/".format(vault.config["clients_dir"], client_note.name)

    def resolved(note):
        out = set()
        for link in note.links:
            rel = vault.resolve_one(link.target, note.rel)
            if rel and rel in vault.notes:
                out.add(rel)
        return out

    chosen = {client_note.rel}
    chosen.update(rel for rel in vault.notes if rel.startswith(folder) and not vault.is_template(rel))
    outgoing = resolved(client_note)
    for note in vault.knowledge_notes():
        if note.rel in chosen or not note.rel.startswith(include):
            continue
        if note.type in NAV_TYPES or _is_client(vault, note) or note.type in knowledge_types:
            continue
        if client_note.rel in resolved(note) or note.rel in outgoing:
            chosen.add(note.rel)

    frontier = set(chosen)
    for _ in range(max(depth, 0)):
        nxt = set()
        for rel in frontier:
            for target in resolved(vault.notes[rel]):
                n = vault.notes[target]
                if target in chosen or vault.is_template(target) or not target.startswith(include):
                    continue
                if n.type in knowledge_types:
                    nxt.add(target)
        chosen |= nxt
        frontier = nxt
        if not nxt:
            break
    return sorted(chosen)


def _unlink_outside(text, vault, source_rel, keep, keep_names, rename):
    """Plain-text every wikilink whose target is not travelling with the client."""
    count = [0]

    def fix(m):
        raw = m.group(2)
        target = re.split(r"\\?\|", raw, 1)[0]
        base = target.split("#", 1)[0].strip()
        rel = vault.resolve_one(base, source_rel) if base else source_rel
        if base.rsplit("/", 1)[-1] in keep_names:
            return m.group(0)
        if rel in keep:
            return m.group(0).replace(base, rename[rel], 1) if rel in rename else m.group(0)
        count[0] += 1
        if re.search(r"\\?\|", raw):
            return re.split(r"\\?\|", raw, 1)[-1]
        return base.rsplit("/", 1)[-1]

    return WIKILINK.sub(fix, text), count[0]


def _scrub(text, patterns, replacement, counts):
    """Replace denied terms. Inside a wikilink the replacement has no brackets, so links stay valid."""
    links = []

    def stash(m):
        links.append(m.group(0))
        return "\x00{}\x00".format(len(links) - 1)

    body = WIKILINK.sub(stash, text)
    for _, term, rx in patterns:
        body, k = rx.subn(replacement, body)
        counts[term] += k
    fixed = []
    for link in links:
        for _, term, rx in patterns:
            link, k = rx.subn("redacted", link)
            counts[term] += k
        fixed.append(link)
    return re.sub("\x00(\\d+)\x00", lambda m: fixed[int(m.group(1))], body)


def _hub_note(name, notes, client, today):
    lines = ["---", "tags: [hub]", "type: hub", "date: {}".format(today), "---", "",
             "# {}".format(name), "", "\u2191 [[Home]]", "",
             "Notes in the {} vault that belong to the {} node.".format(client, name), ""]
    lines += ["- [[{}]]".format(n) for n in notes] or ["No notes in this vault link here yet."]
    return "\n".join(lines) + "\n"


def spinout(vault_root, client, out, denylist_files=(), deny=(), depth=1, force=False, today=None):
    vault = Vault(vault_root)
    note = vault.note_named(client)
    if note is None or not _is_client(vault, note):
        candidates = sorted(n.name for n in vault.knowledge_notes() if _is_client(vault, n))
        raise SpinoutError("no client note named '{}'. Clients: {}".format(client, ", ".join(candidates) or "none"))
    out = os.path.abspath(out)
    if os.path.abspath(vault.root) == out or out.startswith(os.path.abspath(vault.root) + os.sep):
        raise SpinoutError("the output folder must be outside the source vault")
    if os.path.exists(out) and os.listdir(out):
        if not force:
            raise SpinoutError("{} exists and is not empty (use --force to replace it)".format(out))
        shutil.rmtree(out)
    today = today or datetime.date.today().isoformat()
    cfg = vault.config["spinout"]
    replacement = cfg.get("replacement", "[redacted]")

    selected = select(vault, note, depth=depth)
    own_names = {n.lower() for n in _names(note)}

    # Every term that must not survive, with the rule it came from.
    rules = []
    for t in cfg.get("denylist", []):
        rules.append(("config", t))
    for path in denylist_files:
        rules.extend(("file", t) for t in read_denylist(path))
    rules.extend(("cli", t) for t in deny)
    for other in vault.knowledge_notes():
        if other.rel != note.rel and _is_client(vault, other):
            rules.extend(("other-client", n) for n in _names(other) if n.lower() not in own_names)
    seen, terms = set(), []
    for source, term in sorted(rules, key=lambda r: -len(r[1])):  # longest first: "Bluebird Fitness" before "Bluebird"
        if term.strip() and term.lower() not in seen:
            seen.add(term.lower())
            terms.append((source, term.strip()))
    patterns = [(source, term, _term_pattern(term)) for source, term in terms]

    # Notes whose file name carries a denied term get a scrubbed name.
    rename = {}
    for rel in selected:
        name = vault.notes[rel].name
        new = name
        for _, _, rx in patterns:
            new = rx.sub("redacted", new)
        if new != name:
            rename[rel] = UNSAFE_FILENAME.sub("", new).strip()

    keep_names = set(vault.config["hubs"]) | {"Home", "All Notes Index"}
    counts = {term: 0 for _, term in terms}
    unlinked = secrets = 0
    written = []
    for rel in selected:
        text, n = _unlink_outside(vault.notes[rel].text, vault, rel, set(selected), keep_names, rename)
        unlinked += n
        text = _scrub(text, patterns, replacement, counts)
        clean = redact(text)
        if clean != text:
            secrets += 1
        dest_rel = rel if rel not in rename else rel.rsplit("/", 1)[0] + "/" + rename[rel] + ".md"
        dest = os.path.join(out, *dest_rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(clean)
        written.append(dest_rel)

    # Navigation for the new vault: a home note and the four hubs.
    hubs = vault.config["hubs"]
    by_hub = {h: [] for h in hubs}
    for rel in written:
        with open(os.path.join(out, *rel.split("/")), encoding="utf-8") as fh:
            tmp_text = fh.read()
        for h in hubs:
            if "[[{}".format(h) in tmp_text:
                by_hub[h].append(os.path.basename(rel)[:-3])
                break
    client_label = note.title.replace("Client: ", "").strip() or note.name
    for h in hubs:
        _write(os.path.join(out, "01 - Company", h + ".md"), _hub_note(h, sorted(by_hub[h]), client_label, today))
    home = ["---", "tags: [home]", "type: home", "date: {}".format(today), "---", "",
            "# {} Vault".format(client_label), "",
            "> [!abstract] Your notes, as of {}".format(today),
            "> Everything we know and have documented about this engagement, as a standalone Obsidian vault.", "",
            "## Notes", ""]
    for rel in sorted(written):
        home.append("- [[{}]]".format(os.path.basename(rel)[:-3]))
    home += ["", "## Nodes", "", " \u00b7 ".join("[[{}]]".format(h) for h in hubs), "",
             "The [[All Notes Index]] lists every note with a one line summary."]
    _write(os.path.join(out, "00 - Home", "Home.md"), "\n".join(home) + "\n")

    new_cfg = {"name": client_label, "mocs": {}, "forbid_dashes": bool(vault.config.get("forbid_dashes"))}
    _write(os.path.join(out, "agency-os.json"), json.dumps(new_cfg, indent=2) + "\n")
    obs = os.path.join(vault.root, ".obsidian")
    if os.path.isdir(obs):
        shutil.copytree(obs, os.path.join(out, ".obsidian"),
                        ignore=lambda d, names: [n for n in names if n.startswith("workspace")])
        _fix_bookmarks(os.path.join(out, ".obsidian", "bookmarks.json"))
    write_index(Vault(out))

    leaks = verify(out, [t for _, t in terms])
    report = {
        "client": client_label,
        "date": today,
        "notes": sorted(written),
        "notes_in_source": len(vault.knowledge_notes()),
        "links_unlinked": unlinked,
        "notes_with_secrets_redacted": secrets,
        "rules": [{"rule": "rule-{}".format(i + 1), "source": s, "replacements": counts[t]}
                  for i, (s, t) in enumerate(terms)],
        "leaks": len(leaks),
    }
    _write(os.path.join(out, ".agency-os", "spinout-report.json"), json.dumps(report, indent=2) + "\n")
    # The caller (the terminal) may see the actual terms; the file never does.
    report["terms"] = [{"rule": "rule-{}".format(i + 1), "term": t, "source": s, "replacements": counts[t]}
                       for i, (s, t) in enumerate(terms)]
    report["leak_details"] = leaks
    return report


def _ensure(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _write(path, text):
    _ensure(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _fix_bookmarks(path):
    if os.path.exists(path):
        data = {"items": [{"type": "file", "ctime": 1793318400000, "path": "00 - Home/Home.md", "title": "Home"}]}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")


def verify(root, terms):
    """Return ``(file, problem)`` pairs for any denied term or secret shape left in ``root``."""
    patterns = [(t, _term_pattern(t)) for t in terms]
    leaks = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".agency-os"]
        for f in filenames:
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            for t, rx in patterns:
                if rx.search(rel):
                    leaks.append((rel, "term in file name: {}".format(t)))
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            for t, rx in patterns:
                if rx.search(text):
                    leaks.append((rel, "term: {}".format(t)))
            if SECRET_SHAPES.search(text):
                leaks.append((rel, "credential shape"))
    return leaks

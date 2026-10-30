"""Read-only model of an Obsidian vault: notes, frontmatter, wikilinks, resolution.

Only the parts of Obsidian's syntax that matter for integrity are parsed:
YAML-style frontmatter (a flat subset), the H1 title, and ``[[wikilinks]]``
including aliases, headings, block refs, embeds and path-qualified targets.
Links inside fenced code blocks and inline code are ignored, the same way
Obsidian ignores them.
"""

import os
import re

from .config import load_config

WIKILINK = re.compile(r"(!?)\[\[([^\[\]\n]+?)\]\]")
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]*`")
H1 = re.compile(r"^# (.+?)\s*$", re.M)


class Link(object):
    __slots__ = ("target", "line", "embed", "raw")

    def __init__(self, target, line, embed, raw):
        self.target = target
        self.line = line
        self.embed = embed
        self.raw = raw

    def __repr__(self):
        return "Link({!r}, line={})".format(self.target, self.line)


def _scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text):
    """Return ``(fields, body, ok)``.

    ``fields`` maps keys to strings or lists of strings. ``ok`` is False when
    the note has no frontmatter block at all, or the block is never closed.
    """
    if not text.startswith("---"):
        return {}, text, False
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}, text, False
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, False
    fields = {}
    current = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line) or re.match(r"^-\s+(.*)$", line)
        if item and current is not None:
            if not isinstance(fields[current], list):
                fields[current] = []
            fields[current].append(_scalar(item.group(1)))
            continue
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not kv:
            continue
        key, value = kv.group(1), kv.group(2).strip()
        current = key
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fields[key] = [_scalar(v) for v in inner.split(",") if v.strip()] if inner else []
        elif value == "":
            fields[key] = []
        else:
            fields[key] = _scalar(value)
    body = "\n".join(lines[end + 1:])
    return fields, body, True


def code_free_lines(text):
    """Yield ``(line_number, line)`` with fenced blocks dropped and inline code blanked."""
    fence = None
    for n, line in enumerate(text.split("\n"), 1):
        m = FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1) == fence:
                fence = None
            continue
        if fence is not None:
            continue
        yield n, INLINE_CODE.sub("", line)


def parse_links(text):
    links = []
    for n, line in code_free_lines(text):
        for m in WIKILINK.finditer(line):
            raw = m.group(2)
            target = re.split(r"\\?\|", raw, 1)[0]
            target = target.split("#", 1)[0].strip()
            if not target:
                continue  # [[#Heading]] points into the same note
            links.append(Link(target, n, bool(m.group(1)), raw))
    return links


class Note(object):
    def __init__(self, rel, text):
        self.rel = rel
        self.name = os.path.basename(rel)[:-3]
        self.folder = rel.split("/", 1)[0] if "/" in rel else ""
        self.text = text
        self.fields, self.body, self.has_frontmatter = parse_frontmatter(text)
        m = H1.search(self.body)
        self.title = m.group(1).strip() if m else self.name
        self.links = parse_links(text)

    @property
    def type(self):
        value = self.fields.get("type", "")
        return value if isinstance(value, str) else ""

    @property
    def status(self):
        value = self.fields.get("status", "")
        return value if isinstance(value, str) else ""

    @property
    def date(self):
        value = self.fields.get("date", "")
        return value if isinstance(value, str) else ""

    @property
    def tags(self):
        value = self.fields.get("tags", [])
        if isinstance(value, str):
            return [t.strip() for t in value.split(",") if t.strip()]
        return list(value)

    def content_text(self):
        """Body text with headings, rules, frontmatter and whitespace removed."""
        kept = []
        for line in self.body.split("\n"):
            s = line.strip()
            if not s or s.startswith("#") or set(s) <= set("-*_"):
                continue
            kept.append(s)
        return "\n".join(kept)

    def summary(self):
        """First prose line after the H1: what the note is about, in one line."""
        seen_h1 = not H1.search(self.body)
        for _, line in code_free_lines(self.body):
            s = line.strip()
            if not seen_h1:
                if s.startswith("# "):
                    seen_h1 = True
                continue
            if not s or s.startswith(("#", ">", "|", "---", "!", "\u2192", "up:", "<!--")):
                continue
            return s
        return ""


def _norm(path):
    return path.replace(os.sep, "/")


class Vault(object):
    """All notes and attachments under ``root``, plus the vault's config."""

    def __init__(self, root, config=None):
        self.root = os.path.abspath(root)
        if not os.path.isdir(self.root):
            raise FileNotFoundError("vault not found: {}".format(root))
        self.config = config if config is not None else load_config(self.root)
        self.notes = {}
        self.attachments = set()
        self._load()
        self._by_name = {}
        for rel, note in self.notes.items():
            self._by_name.setdefault(note.name.lower(), []).append(rel)
        self._by_file = {}
        for rel in self.attachments:
            self._by_file.setdefault(os.path.basename(rel).lower(), []).append(rel)

    def _load(self):
        exclude = set(self.config["exclude_dirs"])
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in exclude and not d.startswith("."))
            rel_dir = _norm(os.path.relpath(dirpath, self.root))
            rel_dir = "" if rel_dir == "." else rel_dir
            for fname in sorted(filenames):
                if fname.startswith("."):
                    continue
                rel = "{}/{}".format(rel_dir, fname) if rel_dir else fname
                if fname.endswith(".md"):
                    if not rel_dir and fname in ("CLAUDE.md", "README.md"):
                        continue  # instructions for tools, not knowledge notes
                    with open(os.path.join(dirpath, fname), encoding="utf-8", errors="replace") as fh:
                        self.notes[rel] = Note(rel, fh.read())
                elif fname != "agency-os.json":
                    self.attachments.add(rel)

    # -- classification -------------------------------------------------

    def in_dir(self, rel, key):
        d = self.config.get(key, "")
        return bool(d) and (rel == d or rel.startswith(d + "/"))

    def is_template(self, rel):
        return self.in_dir(rel, "templates_dir")

    def is_exempt(self, rel):
        return any(rel.startswith(d + "/") for d in self.config["exempt_dirs"])

    def is_index(self, rel):
        return rel == self.config["index"]

    def is_hub(self, note):
        return note.name in self.config["hubs"] or (
            bool(self.config["company_hub"]) and note.name == self.config["company_hub"])

    def knowledge_notes(self):
        """Notes that are held to the integrity rules (templates excluded)."""
        return [n for rel, n in sorted(self.notes.items()) if not self.is_template(rel)]

    # -- link resolution --------------------------------------------------

    def resolve(self, target):
        """Return the vault-relative paths ``target`` can mean (empty if none)."""
        t = target.strip().replace("\\", "/")
        if t.lower().endswith(".md"):
            t = t[:-3]
        low = t.lower()
        if "/" in t:
            hits = [rel for rel in self.notes if rel[:-3].lower() == low or rel[:-3].lower().endswith("/" + low)]
            hits += [rel for rel in self.attachments if rel.lower() == low or rel.lower().endswith("/" + low)]
            return sorted(hits)
        hits = self._by_name.get(low, [])
        if hits:
            return sorted(hits)
        return sorted(self._by_file.get(low, []))

    def resolve_one(self, target, source_rel=None):
        """Best single match, preferring a note in the source note's folder."""
        hits = self.resolve(target)
        if not hits:
            return None
        if source_rel and len(hits) > 1:
            folder = source_rel.rsplit("/", 1)[0] if "/" in source_rel else ""
            local = [h for h in hits if h.startswith(folder + "/")]
            if local:
                return local[0]
        return hits[0]

    def note_named(self, name):
        rel = self.resolve_one(name)
        return self.notes.get(rel) if rel else None

    def path(self, rel):
        return os.path.join(self.root, *rel.split("/"))


def find_vault(start):
    """Walk up from ``start`` looking for a vault (a dir holding agency-os.json).

    A project folder that contains a vault one level down (``project/vault``)
    also counts, which is the layout ``agency-os init`` creates.
    """
    cur = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(cur, "agency-os.json")):
            return cur
        try:
            children = sorted(os.listdir(cur))
        except OSError:
            children = []
        for child in children:
            cand = os.path.join(cur, child)
            if os.path.isdir(cand) and os.path.isfile(os.path.join(cand, "agency-os.json")):
                return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent

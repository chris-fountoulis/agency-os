"""Vault integrity checks.

Every check is a small function that yields findings. A finding has a check
id, a severity (``error`` or ``warning``), the note it is about, an optional
line number and a human message. Nothing here edits a note.

Checks
  broken-link      a [[wikilink]] that resolves to no note or attachment
  orphan           a note nothing else links to
  no-hub           a note that does not link to any of the four hub nodes
  empty            a note with no content, outside the archive
  generic-name     Untitled, Notes, Misc and friends
  frontmatter      missing block, missing field, unknown type or status, bad date
  duplicate-title  two notes with the same name (ambiguous links) or the same H1
  moc              a note in a MOC folder that its MOC does not list
  dash             em or en dash in prose (only when forbid_dashes is on)
"""

import re

from .vault import code_free_lines

ERROR = "error"
WARNING = "warning"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DASHES = ("\u2014", "\u2013")

CHECKS = (
    "broken-link", "orphan", "no-hub", "empty", "generic-name",
    "frontmatter", "duplicate-title", "moc", "dash",
)


class Finding(object):
    __slots__ = ("check", "severity", "note", "line", "message")

    def __init__(self, check, severity, note, message, line=None):
        self.check = check
        self.severity = severity
        self.note = note
        self.line = line
        self.message = message

    def as_dict(self):
        return {"check": self.check, "severity": self.severity, "note": self.note,
                "line": self.line, "message": self.message}

    def location(self):
        return "{}:{}".format(self.note, self.line) if self.line else self.note


def inbound_counts(vault):
    """Inbound link count per note, ignoring self links, templates and the generated index."""
    counts = {rel: 0 for rel in vault.notes}
    for note in vault.knowledge_notes():
        if vault.is_index(note.rel):
            continue
        seen = set()
        for link in note.links:
            rel = vault.resolve_one(link.target, note.rel)
            if rel and rel != note.rel and rel in counts and rel not in seen:
                counts[rel] += 1
                seen.add(rel)
    return counts


def check_broken_links(vault):
    for note in vault.knowledge_notes():
        for link in note.links:
            if not vault.resolve(link.target):
                yield Finding("broken-link", ERROR, note.rel,
                              "[[{}]] does not resolve to any note or file".format(link.target), link.line)


def check_orphans(vault):
    counts = inbound_counts(vault)
    for note in vault.knowledge_notes():
        if vault.is_exempt(note.rel) or vault.is_hub(note):
            continue
        if counts.get(note.rel, 0) == 0:
            yield Finding("orphan", WARNING, note.rel, "no other note links here")


def _links_to_hub(vault, note):
    hubs = {h.lower() for h in vault.config["hubs"]}
    for link in note.links:
        target = link.target.rsplit("/", 1)[-1].lower()
        if target in hubs:
            return True
    return False


def check_hub_links(vault):
    for note in vault.knowledge_notes():
        if vault.is_exempt(note.rel) or vault.is_hub(note):
            continue
        if not _links_to_hub(vault, note):
            yield Finding("no-hub", ERROR, note.rel, "links to none of the hub nodes ({})".format(
                ", ".join(vault.config["hubs"])))


def check_empty(vault):
    for note in vault.knowledge_notes():
        if vault.in_dir(note.rel, "archive_dir"):
            continue
        if not note.has_content():
            yield Finding("empty", ERROR, note.rel, "note has no content; fill it or move it to the archive")


def check_generic_names(vault):
    patterns = [re.compile(p, re.I) for p in vault.config["generic_names"]]
    for note in vault.knowledge_notes():
        if any(p.fullmatch(note.name.strip()) for p in patterns):
            yield Finding("generic-name", ERROR, note.rel,
                          "'{}' says nothing about the subject; rename it".format(note.name))


def check_frontmatter(vault):
    cfg = vault.config
    types = set(cfg["types"])
    statuses = set(cfg["statuses"])
    optional = set(cfg["status_optional_types"])
    for note in vault.knowledge_notes():
        if not note.has_frontmatter:
            yield Finding("frontmatter", ERROR, note.rel, "no frontmatter block", 1)
            continue
        for key in cfg["required_fields"]:
            if key == "status" and note.type in optional:
                continue
            value = note.fields.get(key)
            if value is None or value == "" or value == []:
                yield Finding("frontmatter", ERROR, note.rel, "missing '{}'".format(key), 1)
        if note.type and note.type not in types:
            yield Finding("frontmatter", ERROR, note.rel, "type '{}' is not in the vocabulary".format(note.type), 1)
        if note.status and note.status not in statuses:
            yield Finding("frontmatter", ERROR, note.rel, "status '{}' is not in the vocabulary".format(note.status), 1)
        if note.date and not DATE.match(note.date):
            yield Finding("frontmatter", ERROR, note.rel, "date '{}' is not YYYY-MM-DD".format(note.date), 1)


def check_duplicates(vault):
    by_name = {}
    by_title = {}
    for note in vault.knowledge_notes():
        by_name.setdefault(note.name.lower(), []).append(note.rel)
        by_title.setdefault(note.title.strip().lower(), []).append(note.rel)
    for rels in by_name.values():
        if len(rels) > 1:
            for rel in rels:
                others = ", ".join(r for r in rels if r != rel)
                yield Finding("duplicate-title", ERROR, rel,
                              "same note name as {} (links become ambiguous)".format(others))
    names_dup = {tuple(r) for r in by_name.values() if len(r) > 1}
    for rels in by_title.values():
        if len(rels) > 1 and tuple(rels) not in names_dup:
            for rel in rels:
                others = ", ".join(r for r in rels if r != rel)
                yield Finding("duplicate-title", WARNING, rel, "same H1 title as {}".format(others))


def check_mocs(vault):
    for folder, moc_rel in sorted(vault.config["mocs"].items()):
        moc = vault.notes.get(moc_rel)
        members = [n for n in vault.knowledge_notes() if n.rel.startswith(folder + "/") and n.rel != moc_rel]
        if moc is None:
            if members:
                yield Finding("moc", WARNING, members[0].rel, "folder '{}' has no MOC at {}".format(folder, moc_rel))
            continue
        listed = set()
        for link in moc.links:
            rel = vault.resolve_one(link.target, moc.rel)
            if rel:
                listed.add(rel)
        for note in members:
            if note.rel not in listed:
                yield Finding("moc", WARNING, note.rel, "not listed in {}".format(moc.name))


def check_dashes(vault):
    if not vault.config.get("forbid_dashes"):
        return
    for note in vault.knowledge_notes():
        for n, line in code_free_lines(note.text):
            if line.startswith("# "):
                continue
            stripped = re.sub(r"\[\[[^\]]*\]\]", "", line)
            if any(d in stripped for d in DASHES):
                yield Finding("dash", WARNING, note.rel, "em or en dash in prose", n)


RUNNERS = (
    check_broken_links, check_orphans, check_hub_links, check_empty, check_generic_names,
    check_frontmatter, check_duplicates, check_mocs, check_dashes,
)


class LintResult(object):
    def __init__(self, vault, findings):
        self.vault = vault
        self.findings = findings

    @property
    def errors(self):
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self):
        return [f for f in self.findings if f.severity == WARNING]

    def link_count(self):
        return sum(len(n.links) for n in self.vault.knowledge_notes())

    def as_dict(self):
        counts = {}
        for f in self.findings:
            counts[f.check] = counts.get(f.check, 0) + 1
        return {
            "vault": self.vault.root,
            "notes": len(self.vault.knowledge_notes()),
            "links": self.link_count(),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "counts": counts,
            "findings": [f.as_dict() for f in self.findings],
        }


def lint(vault, ignore=()):
    findings = []
    for runner in RUNNERS:
        for finding in runner(vault):
            if finding.check not in ignore:
                findings.append(finding)
    findings.sort(key=lambda f: (f.note, f.line or 0, f.check))
    return LintResult(vault, findings)

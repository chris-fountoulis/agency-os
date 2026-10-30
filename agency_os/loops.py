"""Read the Open Loops Register: the rows of the table under its ``## Open`` heading."""

import datetime
import re

from .vault import WIKILINK


def _cells(line):
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    # A pipe inside a wikilink alias is escaped as \| in tables; keep it intact.
    parts = re.split(r"(?<!\\)\|", inner)
    return [p.strip() for p in parts]


def _plain(cell):
    return WIKILINK.sub(lambda m: re.split(r"\\?\|", m.group(2), 1)[-1].split("#")[0], cell).strip()


def parse_table(lines):
    rows, header = [], None
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            if header is not None and rows:
                break
            continue
        cells = _cells(s)
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        row = {header[i]: cells[i] for i in range(min(len(header), len(cells)))}
        rows.append(row)
    return rows


def open_loops(vault, today=None):
    """Open loops as dicts with plain-text values plus ``overdue`` and ``links``."""
    note = vault.notes.get(vault.config["open_loops"])
    if note is None:
        return []
    section, capture = [], False
    for line in note.body.split("\n"):
        if line.startswith("## "):
            capture = line[3:].strip().lower() == "open"
            continue
        if capture:
            section.append(line)
    today = today or datetime.date.today().isoformat()
    loops = []
    for row in parse_table(section):
        item = {k: _plain(v) for k, v in row.items()}
        item["links"] = [m.group(2).split("|")[0].split("#")[0].strip()
                         for v in row.values() for m in WIKILINK.finditer(v)]
        due = item.get("due", "")
        item["overdue"] = bool(re.match(r"^\d{4}-\d{2}-\d{2}$", due)) and due < today
        loops.append(item)
    return loops

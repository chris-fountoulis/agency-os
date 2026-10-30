"""Vault statistics: size, link density, orphan rate, hub coverage, activity.

The generated index is left out of every number: it links every note by
design, and counting it would make every vault look perfectly connected.
"""

import re

from .lint import _links_to_hub, inbound_counts
from .loops import open_loops
from .term import Painter, bar

SESSION_ENTRY = re.compile(r"^## \d{2}:\d{2} ", re.M)


def compute(vault):
    notes = [n for n in vault.knowledge_notes() if not vault.is_index(n.rel)]
    eligible = [n for n in notes if not vault.is_exempt(n.rel) and not vault.is_hub(n)]
    inbound = inbound_counts(vault)

    resolved = broken = 0
    edges = set()
    for n in notes:
        for link in n.links:
            rel = vault.resolve_one(link.target, n.rel)
            if rel:
                resolved += 1
                if rel != n.rel:
                    edges.add((n.rel, rel))
            else:
                broken += 1

    orphans = [n.rel for n in eligible if inbound.get(n.rel, 0) == 0]
    with_hub = [n.rel for n in eligible if _links_to_hub(vault, n)]

    by_folder, by_type = {}, {}
    for n in notes:
        by_folder[n.folder or "(root)"] = by_folder.get(n.folder or "(root)", 0) + 1
        by_type[n.type or "(none)"] = by_type.get(n.type or "(none)", 0) + 1

    sessions = [n for n in notes if vault.in_dir(n.rel, "sessions_dir") and n.type == "session"]
    entries = sum(len(SESSION_ENTRY.findall(n.body)) for n in sessions)
    latest = max((n.date for n in sessions), default="")

    words = sum(len(re.findall(r"\w+", n.body)) for n in notes)
    top = sorted(((c, rel) for rel, c in inbound.items() if c and not vault.is_index(rel)),
                 key=lambda x: (-x[0], x[1]))[:5]

    loops = open_loops(vault)
    return {
        "name": vault.config.get("name", ""),
        "notes": len(notes),
        "words": words,
        "links": resolved + broken,
        "broken_links": broken,
        "unique_edges": len(edges),
        "link_density": round(float(resolved) / len(notes), 2) if notes else 0.0,
        "orphans": len(orphans),
        "orphan_rate": round(100.0 * len(orphans) / len(eligible), 1) if eligible else 0.0,
        "hub_coverage": round(100.0 * len(with_hub) / len(eligible), 1) if eligible else 100.0,
        "open_loops": len(loops),
        "session_logs": len(sessions),
        "session_entries": entries,
        "latest_session": latest,
        "by_folder": dict(sorted(by_folder.items())),
        "by_type": dict(sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0]))),
        "most_linked": [{"note": vault.notes[rel].name, "inbound": c} for c, rel in top],
    }


def render(stats, label, paint=None):
    paint = paint or Painter()
    k = lambda s: paint(s, "dim")
    v = lambda s: paint(str(s), "bold")
    title = "agency-os stats  {}".format(label)
    if stats["name"]:
        title += "  ({})".format(stats["name"])
    out = [paint(title, "gold", "bold"), ""]
    pairs = [
        ("Notes", "{:,}".format(stats["notes"]), "Words", "{:,}".format(stats["words"])),
        ("Links", "{:,}".format(stats["links"]), "Link density", "{} per note".format(stats["link_density"])),
        ("Orphan rate", "{}%".format(stats["orphan_rate"]), "Hub coverage", "{}%".format(stats["hub_coverage"])),
        ("Open loops", stats["open_loops"], "Session entries", "{}{}".format(
            stats["session_entries"], " (latest {})".format(stats["latest_session"]) if stats["latest_session"] else "")),
    ]
    for a, av, b, bv in pairs:
        out.append("  {} {}   {} {}".format(k("{:<12}".format(a)), v("{:>8}".format(av)), k("{:<16}".format(b)), v(bv)))
    if stats["broken_links"]:
        out.append("  " + paint("{} broken links: run agency-os lint".format(stats["broken_links"]), "red"))

    def section(name, items):
        if not items:
            return
        out.append("")
        out.append("  " + paint(name, "bold"))
        width = max(len(key) for key, _ in items)
        peak = max(count for _, count in items)
        for key, count in items:
            out.append("    {}  {} {}".format(key.ljust(width), paint(bar(count, peak, 20).ljust(20), "gold"), count))

    section("By folder", list(stats["by_folder"].items()))
    section("By type", list(stats["by_type"].items()))
    section("Most linked", [(m["note"], m["inbound"]) for m in stats["most_linked"]])
    return "\n".join(out)

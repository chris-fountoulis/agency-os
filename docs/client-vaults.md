<p align="right"><a href="../README.md">Back to README</a></p>

# Client vaults

`agency-os spinout` turns one client's slice of the company vault into a standalone Obsidian
vault: their notes, the projects and meetings that mention them, and the SOPs and resources
those link to. Nothing about anyone else. Use it to hand a client their documentation, to give a
contractor exactly one account, or to seed a per-client vault that a client-facing Claude Code
setup can read whithout seeing the rest of the company.

| Step | What happens |
|---|---|
| [Select](#what-gets-selected) | The client note, what links to it and the knowledge it uses |
| [Scrub](#what-gets-scrubbed) | Dropped links, denied terms, other clients' names, credentials |
| [Verify](#the-leak-check) | Every output file re-scanned; any hit fails the run |
| [Deliver](#what-you-get) | A standalone vault that passes `agency-os lint --strict` |

```bash
agency-os spinout vault --client "Acme Bakery" --out ../acme-bakery-vault \
  --denylist team-names.txt --deny "Project Lighthouse" --depth 2
```

## What gets selected

1. The client note, and everything in `02 - Clients/<Client>/` if the client has a folder.
2. Notes in `spinout.include_folders` (projects, knowledge base, meetings, resources by default)
   that link to the client note or that the client note links to. Navigation notes (MOCs, hubs,
   trackers), session logs and other clients are never selected.
3. Linked knowledge : notes of `spinout.knowledge_types` (SOPs, resources, concepts) that the
   selection links to, followed `--depth` levels (default 1).

The open loops register, the decision log, the team directory and session logs never travel:
they are company-wide by nature.

## What gets scrubbed

For every selected note , in this order:

1. **Links to notes left behind become plain text.** No dangling links, no hint of what was
   there beyond the visible text, which the next steps scrub.
2. **Denylisted terms are replaced** with `[redacted]` (`redacted` inside a wikilink , so links
   stay valid). Terms come from:
   - `spinout.denylist` in `agency-os.json`: things that never leave the company
     (internal codenames, margin language, payroll);
   - `--denylist FILE`: one term per line, `#` comments;
   - `--deny TERM`: one-off terms;
   - **every other client's note name, H1 and `aliases`**, automatically. Add short names to a
     client note as `aliases: [Bluebird]` so "Bluebird" is caught as well as "Bluebird Fitness".

   Matching is case-insensitive on word boundaries, longest term first.
3. **Credential shapes are redacted** with the same rules the session logger uses.

File names that contain a denied term are renamed , and links to them are rewritten to match.

## The leak check

After writing every file in the output is scanned again for every denied term and every
credential shape. Any hit is listed and the command exits `1`. A clean run says so:

```text
  verified: no denylisted term or credential shape left in the output
```

The report saved at `<out>/.agency-os/spinout-report.json` lists the selected notes and counts
replacements per rule (`rule-1`, `rule-2`, ...) **without naming the terms**, so the report
inside the client's vault cannot leak what was removed. The terminal output , which only you see,
does name them.

## What you get

- The selected notes in their original folders.
- A generated `00 - Home/Home.md` for the client and the four hub notes , listing what is inside.
- A fresh `agency-os.json` (the source denylist is not copied), the shared `.obsidian/` settings
  and a regenerated All Notes Index. The result passes `agency-os lint --strict`.

## Before you share it

> [!WARNING]
> Read every note once. The scrub removes names it knows about. It cannot know that a sentence
> about a client's churn risk is not for their eyes.

Team members' names are not scrubbed unless you list them. Put them in a denylist file if the
client should not see who did what.

---

<p align="right"><a href="../README.md">Back to README</a></p>

<p align="center">Built by <a href="https://chrisfountoulis.com">Chris Fountoulis</a> at <a href="https://growthofinfluence.com">Growth Of Influence</a>.</p>

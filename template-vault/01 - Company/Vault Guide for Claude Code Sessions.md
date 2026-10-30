---
tags: [vault, guide, system]
type: system
status: active
date: 2026-10-30
---

# Vault Guide for Claude Code Sessions

→ [[Management]]

The first note a Claude Code session reads. What this vault is, where things live, how to find a fact fast, and the exact shape of a new note. Read it before you touch a client, a price or a promise.

## What this vault is

The shared memory of Northwind Studio. It holds clients, projects, SOPs, decisions and open commitments, so a session never has to rebuild context from a chat log and a new team member inherits everything on day one. Every person on the team and every Claude Code session reads from it and writes to it.

## The four nodes

Every note links to exactly one node on the line under its H1, written as `→ [[Node]]`. This is the spine of the graph.

| Node | Covers | Tie-breaker |
|---|---|---|
| [[Sales]] | Clients, proposals, pipeline | 1st |
| [[Product]] | Services, scope, delivery | 2nd |
| [[Marketing]] | Our own brand, content, channels | 3rd |
| [[Management]] | Team, decisions, internal systems, this vault | 4th |

When a note could sit under two nodes, pick the higher rank. [[Northwind Studio]] sits above all four.

## Folder map

| Folder | What goes here |
|---|---|
| `00 - Home/` | The [[Home]] dashboard and the generated [[All Notes Index]] |
| `01 - Company/` | Company facts, the hubs, this guide, the [[Open Loops Register]], decisions |
| `02 - Clients/` | One note per client, listed in [[Clients MOC]] |
| `03 - Projects/` | Initiatives with an owner and an end, listed in [[Projects MOC]] |
| `04 - Knowledge Base/` | SOPs and playbooks, listed in [[Knowledge Base MOC]] |
| `05 - Meetings/` | One note per meeting, listed in [[Meetings MOC]] |
| `06 - Resources/` | Tools, glossaries, reference, listed in [[Resources MOC]] |
| `07 - Templates/` | Copy these, never edit them in place |
| `08 - Sessions/` | Written by the session hook. Do not write these by hand |
| `99 - Archive/` | Retired notes. Never delete a note, move it here |

## Entry points, in order

Stop as soon as you have what you need.

1. `CLAUDE.md` in the project folder: identity, hard rules, pointers.
2. `vault-autopilot.md`: the capture protocol, what to write back and where.
3. This guide.
4. [[Open Loops Register]]: read it before promising anything.
5. [[Clients MOC]]: every client with a one line status.
6. [[All Notes Index]]: one row per note, the fastest way to find anything.

## How to find things

- **One grep answers most questions.** The [[All Notes Index]] has one row per note with its type, status, date and summary. Search it first.
- **By client:** the client note links its projects, meetings and the SOPs used.
- **By situation:** the [[Knowledge Base MOC]] is grouped by the situation you are in, not by title.
- **History:** the newest session logs in `08 - Sessions/` say what changed recently and who changed it.

## Writing a note

Frontmatter, exactly these keys:

```yaml
---
tags: [lowercase, hyphenated, specific-then-general]
type: client | project | sop | decision | meeting | open-loop | tracker | resource | system
status: active | draft | open | paused | done | closed | archived
date: 2026-10-30
---
```

Client notes may also carry `aliases: [Short Name]`: Obsidian resolves links through them, and a client spinout scrubs every other client's name and aliases.

Body shape:

1. H1 title that names the subject: `# Client: Client Name`, `# SOP, Client Onboarding`.
2. The arrow line: `→ [[Sales]]`. Exactly one node.
3. A one line summary, so a reader knows in five seconds whether to keep reading.
4. Sections.
5. `## Related` as the last section. Only real links, verified before writing.

## Hard rules

- **Update facts in place.** When a fact changes, change it where it lives and set `date:` to today. Never append a correction under the old text; two versions of a fact is worse than none.
- **One note, one subject.** A client, an SOP, a decision. Not one fact: a single fact is a line in an existing note.
- **Search before you create.** A duplicate note splits the memory in two.
- **Never copy a secret.** Record what a credential is and where it lives, never its value.
- **Never leave a note empty.** Fill it or move it to `99 - Archive/`.
- **Add every new note to its MOC** and link it from at least one other note.
- **Run `agency-os lint`** after you write. A clean lint is the definition of done.

## Related

- Capture protocol: [[SOP, Capturing Knowledge From a Session]]
- Client handover: [[SOP, Spinning Out a Client Vault]]
- Decision behind this vault: [[Decision, One Vault for the Whole Team]]

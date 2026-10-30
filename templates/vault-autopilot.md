# Vault autopilot: the capture protocol

The standing instruction for every Claude Code session in this project: capture durable
knowledge into the vault at `{{VAULT_DIR}}/` as it appears, with the right schema, in the right
place, linked into the graph, without duplicates. Capture mid-session as facts land, and again in
one pass before you stop. Session *logs* are not your job: the Stop hook writes them.

## 1. What to capture

Capture anything a teammate or a future session would need and could not cheaply rediscover.

| Kind | Capture when | Example |
|---|---|---|
| **Decision** | A choice was made that changes how work is done, with a reason | "Pre-orders use the shop's booking tool, not a custom form" |
| **Fact** | Something true about a client, a tool, a person or the company that will still be true next month | "The owner approves prices; the manager approves captions" |
| **Status change** | A client, project or loop moved: started, approved, paused, shipped, closed | "Sitemap approved 2026-10-28" |
| **SOP** | A procedure worked and will be repeated | "How we hand a client their own vault" |
| **Open loop** | Anyone promised anything to anyone, or a decision is pending | "Send the wireframe by Monday" |

**Do not capture:** chit-chat, intermediate debugging, anything already in git history, guesses
presented as facts, and secrets of any kind (record *where* a credential lives, never its value).

## 2. Where it goes (routing)

| Kind | Destination |
|---|---|
| Client fact or status | `02 - Clients/<Client>.md`: Key facts, History, and `status:` |
| Project fact or status | `03 - Projects/<Project>.md`: Milestones, Decisions, `status:` |
| Decision that changes how the company works | A new note in `01 - Company/Decisions/` from the Decision Record template, plus a row in the Decision Log |
| Decision local to one client or project | A line in that note's Decisions section |
| SOP | A new note in `04 - Knowledge Base/` from the SOP template, listed in the Knowledge Base MOC under the situation it is for |
| Open loop | One row in the `## Open` table of `01 - Company/Open Loops Register.md`. Close it by moving the row to `## Closed` with the outcome |
| Meeting | A note in `05 - Meetings/` named `YYYY-MM-DD <Topic>.md` |
| Tool or reference | `06 - Resources/` |

When a note could sit under two hubs, the tie-breaker is Sales, then Product, then Marketing,
then Management.

## 3. Dedup before you write

1. Search first: the All Notes Index (`00 - Home/All Notes Index.md`), then a full-text search
   for the client, project or key term.
2. If a note on the subject exists, **update it in place**. Replace a fact that changed; do not
   stack the new version under the old one. Set `date:` to today.
3. Create a new note only for a new subject (a client, a project, an SOP, a decision). A single
   new fact is a line in an existing note, never its own note.
4. Never create a second note for the same subject under a different name. If you find two,
   merge them and move the loser to `99 - Archive/`.

## 4. Linking (every new note, no exceptions)

1. **Frontmatter:** `tags`, `type`, `status`, `date` (YYYY-MM-DD), using the vocabulary in the
   Vault Guide.
2. **Hub arrow:** the line under the H1 is `→ [[Sales]]` (or Product, Marketing, Management).
3. **One line summary** right after the arrow.
4. **MOC:** add the note to its folder's MOC the same turn.
5. **Inbound link:** at least one other relevant note links to it (the client note links its
   project; the project links its meeting).
6. **`## Related`** as the last section, with only links you have verified exist.

## 5. Finish

Run `agency-os lint {{VAULT_DIR}}`. Errors are not optional: fix broken links, missing hub
links, missing frontmatter and empty notes before you stop. Run `agency-os index {{VAULT_DIR}}`
when you added or renamed notes. Then tell the person, in one line, what you captured and where.

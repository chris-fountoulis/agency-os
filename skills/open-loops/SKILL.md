---
name: open-loops
description: Show, add or close open loops (commitments, promises to clients, pending decisions) in the vault's Open Loops Register. Use when the user asks what is open, what is overdue, what was promised to a client, or says to add, track, close or follow up on a commitment.
argument-hint: "[list | overdue | add <loop> | close <loop>]"
---

# Open loops

The Open Loops Register (`01 - Company/Open Loops Register.md` in the vault) is the single list of every commitment that is not closed. Request: $ARGUMENTS

## List (default) or overdue

Run from the project folder:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" loops
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" loops --overdue
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" loops --owner <name>
```

Show the result grouped by owner, overdue first. For each overdue loop, say in one line what the next action is, using the client or project note it links to.

## Add

1. Confirm the loop has an owner, a due date (YYYY-MM-DD) and a place it belongs (a client or project note). Ask only for what is missing.
2. Add one row to the `## Open` table: `| What was promised | Owner | Opened (today) | Due | [[Client or Project]] |`.
3. Add a History line to the linked client or project note.

## Close

1. Move the row from `## Open` to `## Closed` with today's date and the outcome in one line. Never delete a row.
2. Update the linked note's status or History.

## Finish

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" lint <vault>` and fix any error you introduced.

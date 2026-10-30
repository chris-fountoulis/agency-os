---
tags: [sop, vault, claude-code, capture]
type: sop
status: active
date: 2026-10-30
---

# SOP, Capturing Knowledge From a Session

→ [[Management]]

What a Claude Code session writes back into the vault while it works and before it stops, so the next session starts knowing it. The full protocol is `vault-autopilot.md` in the project folder; this is the short version.

## What gets captured

| Kind | Example | Where it goes |
|---|---|---|
| Decision | "We use the booking tool for pre-orders" | The project or client note, plus a decision note if it changes how we work |
| Fact | "The owner approves prices" | The client note, Key facts |
| Status change | "Sitemap approved" | The note's `status:`, its History, and the MOC line |
| SOP | A procedure that worked and will be repeated | A new note in `04 - Knowledge Base/` |
| Open loop | "Send the wireframe by Monday" | A row in the [[Open Loops Register]] |

## Rules

1. Search before writing. Update the existing note in place; do not create a second one.
2. Replace a fact that changed. Do not stack the new version under the old one.
3. Every new note links one hub, gets listed in its MOC, and is linked from at least one other note.
4. Run `agency-os lint` and fix what it reports.
5. Session logs are written by the Stop hook. Do not write them by hand.

## Related

- Rules of the vault: [[Vault Guide for Claude Code Sessions]]

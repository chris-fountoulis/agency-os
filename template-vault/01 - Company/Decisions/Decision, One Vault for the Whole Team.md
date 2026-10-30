---
tags: [decision, vault, management]
type: decision
status: done
date: 2026-10-05
---

# Decision, One Vault for the Whole Team

→ [[Management]]

All company knowledge lives in one shared vault in git, read by every Claude Code session at start, instead of personal notes and chat history.

## Context

Client facts lived in five places: chat threads, personal notes, email and two people's heads. Each Claude Code session started from zero and had to be briefed by hand.

## Options considered

1. Keep personal notes and brief each session by hand.
2. A shared drive folder of documents.
3. One vault in a git repo, with session hooks that read it at start and log back at the end.

## Decision

Option 3. Git gives history and review; the hooks make reading and writing the vault the default instead of a habit someone has to remember.

## Consequences

- Every new fact goes into the vault the moment it lands, through [[SOP, Capturing Knowledge From a Session]].
- `agency-os lint` runs before every push.
- Client work can be handed over as a standalone vault: [[SOP, Spinning Out a Client Vault]].

## Related

- Log: [[Decision Log]]

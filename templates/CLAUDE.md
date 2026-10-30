# {{COMPANY}}: operating instructions for Claude Code

> **How this file is organized (read once).** This file holds stable identity, hard rules and
> pointers to where current state lives. It is not a log. Debugging history, SOP narratives and
> changelogs belong in the vault (`{{VAULT_DIR}}/`), not here. When a fact changes, **update the
> fact in place**. Never append a correction under the old text: two versions of a fact is worse
> than none, because the next session cannot tell which one is current.

## Who we are

- **Company:** {{COMPANY}}
- **What we do:** (one line: the services you sell, to whom)
- **Team:** (names and roles, one line each; the full list lives in the vault's Team Directory)
- **Where we are going:** (one line on the client roadmap: who you serve now, who next)

## How we work

- Lead with the result. First line of every reply: what is done, or what is blocked.
- One recommendation, not a menu of equal options. Say why in a sentence.
- Small decisions are yours. Stop and ask only for things that are destructive, irreversible or
  outward facing (an email to a client, anything published under the company's name).
- Report faithfully. "Verified" means you ran it and saw the output.

## Hard rules (no exceptions)

1. **Never send, publish or promise anything to a client** without a person approving it first.
2. **Never write a secret into the vault or any file.** Record what a credential is and where it
   lives, never its value.
3. **No client name, logo or result goes into public material** without a written consent record
   filed in the client's note.
4. **No promises about outcomes.** We promise work, reporting and dates, never results.
5. (Add the rules your team has learned the hard way. Keep each one a single line with the reason.)

## The vault is the memory

The company's shared memory is the Obsidian vault at `{{VAULT_DIR}}/`. Every session reads it
before working and writes back what it learned.

**At the start of every session** (the SessionStart hook prints a reminder with the latest
session summaries and open loops):

1. Read `{{VAULT_DIR}}/01 - Company/Vault Guide for Claude Code Sessions.md`.
2. Read `vault-autopilot.md` next to this file: the capture protocol.
3. Before promising anything, read `{{VAULT_DIR}}/01 - Company/Open Loops Register.md`.

**While working:** capture durable knowledge as it lands (decisions, facts, status changes, SOPs,
open loops) following `vault-autopilot.md`. Update notes in place; never duplicate.

**Before stopping:** run `agency-os lint {{VAULT_DIR}}` and fix every error. Run
`agency-os index {{VAULT_DIR}}` if you added or renamed notes. The Stop hook writes the session
log to `{{VAULT_DIR}}/08 - Sessions/`; do not write session logs by hand.

## Where current state lives

| Question | Note |
|---|---|
| What is open, promised or waiting? | `01 - Company/Open Loops Register.md` |
| Who is this client, what did we promise? | `02 - Clients/<Client>.md` |
| How do we do X? | `04 - Knowledge Base/Knowledge Base MOC.md` |
| Why did we decide Y? | `01 - Company/Decision Log.md` |
| What happened recently? | the newest files in `08 - Sessions/` |
| Everything, one row per note | `00 - Home/All Notes Index.md` |

## Tools

- `agency-os lint | index | stats | loops | spinout | session-log` (see `agency-os --help`)
- (Add the tools, servers and accounts sessions need, with where each credential lives. Never
  the value.)

_Last structural review: {{DATE}}._

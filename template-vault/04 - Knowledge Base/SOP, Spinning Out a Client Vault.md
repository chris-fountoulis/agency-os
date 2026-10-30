---
tags: [sop, vault, clients, spinout]
type: sop
status: active
date: 2026-10-30
---

# SOP, Spinning Out a Client Vault

→ [[Management]]

How to give a client a standalone vault with their notes and the knowledge linked to them, and nothing about anyone else.

## Steps

1. Make sure the client note and its projects are current. Lint the vault.
2. Add any internal terms that must never leave the studio to `spinout.denylist` in `agency-os.json`.
3. Run `agency-os spinout <vault> --client "<Client>" --out <folder>`.
4. Read the report. Every scrubbed term is counted; the run fails if any denylisted term survives.
5. Open the new vault in Obsidian and read every note once before it is shared.

## What is never included

- Other clients' notes, and their names anywhere in the copied text.
- Session logs, the open loops register, decisions and the team directory.
- Anything matching a credential pattern.

## Related

- Rules of the vault: [[Vault Guide for Claude Code Sessions]]

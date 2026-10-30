---
name: capture
description: Capture durable knowledge from this session into the company Obsidian vault (decisions, facts, status changes, SOPs, open loops), updating notes in place, linking them into the graph and finishing with a clean lint. Use when the user says capture, save this to the vault, remember this for the team, log the decision, or at the end of substantial work.
argument-hint: "[what to capture, optional]"
---

# Capture to the vault

Capture what this session learned into the company vault so every teammate and every future session inherits it. If arguments were given, capture exactly that: $ARGUMENTS

## 1. Find the vault and the rules

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" context` from the project folder. It prints the vault path, the Vault Guide path and the open loops. If it reports no vault, tell the user to run `agency-os init` and stop.

Read the Vault Guide it names. If the project has a `vault-autopilot.md`, read it: it is the authority on routing and wins over this skill where they differ.

## 2. List what is worth keeping

Go through the conversation and list candidates in five kinds. Keep only what a teammate would need next month and could not cheaply rediscover.

| Kind | Keep when |
|---|---|
| Decision | A choice was made with a reason |
| Fact | It will still be true next month (a client preference, an approval rule, where a credential lives) |
| Status change | A client, project or loop moved |
| SOP | A procedure worked and will be repeated |
| Open loop | Someone promised something, or a decision is pending |

Never capture a secret value. Record what the credential is and where it lives.

## 3. Route, dedup, write

For each candidate:

1. Search the `00 - Home/All Notes Index.md` and grep the vault for the subject first.
2. If a note exists, **update it in place**: replace the old fact, never stack a correction under it, set `date:` to today.
3. If it needs a new note, copy the matching template from `07 - Templates/`, put it in the right numbered folder, and give it the four frontmatter keys (`tags`, `type`, `status`, `date`), the hub arrow line (`→ [[Sales]]` or Product, Marketing, Management) and a one line summary.
4. Add every new note to its folder's MOC, and link it from at least one related note.
5. Open loops are rows in the `## Open` table of `01 - Company/Open Loops Register.md`, not new notes.

## 4. Verify

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" lint <vault>` and fix every error. If you created or renamed notes, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" index <vault>`.

## 5. Report

One short list: each item captured, the note it went into, and whether it was new or updated. Do not write a session log; the Stop hook does that.

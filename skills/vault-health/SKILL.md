---
name: vault-health
description: Check the company Obsidian vault for integrity problems (broken links, orphans, notes missing a hub link or frontmatter, empty or generically named notes, duplicates) and fix them. Use when the user asks to check, clean, lint or tidy the vault, or before sharing or spinning out a client vault.
argument-hint: "[fix]"
---

# Vault health

Request: $ARGUMENTS

## 1. Measure

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" stats <vault>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agency-os" lint <vault> --format json
```

Summarise: notes, link density, orphan rate, hub coverage, then the lint findings grouped by check, errors first.

## 2. Fix (only when asked to fix, or when the user agrees)

Work through errors before warnings. Never delete a note: move it to `99 - Archive/`.

| Check | Fix |
|---|---|
| broken-link | Find the intended note (it may have been renamed) and correct the link. If the target never existed, create it only when it is a real subject; otherwise unlink the text |
| no-hub | Add the arrow line under the H1 with the one hub the note belongs to |
| frontmatter | Add the missing keys with values from the Vault Guide's vocabulary |
| empty | Fill it from what the vault already knows, or move it to `99 - Archive/` |
| generic-name | Rename it after its subject and update every link to it |
| duplicate-title | Merge the two notes into one, keep the better name, archive the other |
| orphan | Link it from its MOC and from the most related note |
| moc | Add a line for the note to its folder's MOC |

## 3. Verify

Run lint again until it reports no errors, then `index` to refresh the All Notes Index. Report what changed in one short list.

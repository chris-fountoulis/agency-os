# Team setup: several people, one vault

The vault is a git repository. Each person has a clone, opens it in Obsidian, and runs Claude
Code with the agency-os plugin from the project folder that contains it. Sessions read the same
memory, session logs land in per-person files so they never conflict, and a background sync
keeps every clone current.

## 1. One person creates the vault

```bash
git clone https://github.com/chris-fountoulis/agency-os
python3 agency-os/scripts/agency-os init ~/work/acme-brain --name "Acme Agency" --no-examples

cd ~/work/acme-brain
git init -b main
git add -A && git commit -m "vault: initial scaffold"
git remote add origin git@github.com:acme-agency/acme-brain.git   # a PRIVATE repository
git push -u origin main
```

Keep the repository private. A company vault holds client facts by design.

Fill in `CLAUDE.md` (who you are, the hard rules you have learned) before inviting anyone. Every
session on the team reads it.

## 2. Everyone else joins

```bash
git clone git@github.com:acme-agency/acme-brain.git ~/work/acme-brain
```

Then, once per person:

1. **Obsidian:** Open folder as vault, pick `~/work/acme-brain/vault`. The shared settings in
   `.obsidian/` (templates folder, graph colours, the CSS snippet, bookmarks) come with the
   clone; per-person layout (`workspace.json`) is gitignored.
2. **Claude Code plugin:**
   ```text
   /plugin marketplace add chris-fountoulis/agency-os
   /plugin install agency-os@agency-os
   ```
   Or without the plugin: `agency-os init --hooks` writes the same three hooks into the
   project's `.claude/settings.json`, which you commit so the whole team gets them.
3. **Name in the logs:** session logs are named after `git config user.name` in the vault repo,
   or `AGENCY_OS_PERSON` if set. Make sure each person's name is set.
4. **Sync (optional, recommended):** `agency-os/sync/install.sh ~/work/acme-brain`. Every minute
   it commits local changes, pulls teammates' changes and pushes. See [sync/README.md](../sync/README.md).

## How conflicts are avoided

| Writes | How it stays conflict-free |
|---|---|
| Session logs | One file per person per day: `2026-10-30 Sessions, alex.md` |
| Checkpoints | One file per compaction, named by time and session id |
| The index | Generated; regenerate after a pull instead of merging it by hand |
| Notes | Small, one subject each, updated in place: two people rarely edit the same lines |

When two people do edit the same lines, the sync rebase stops, nothing is lost, and the person
whose run hit it gets one notification to resolve it in their editor.

## Rules worth agreeing on day one

- **Who approves what.** Write it into `CLAUDE.md`'s hard rules. Sessions follow it.
- **Lint before push.** `agency-os lint vault` in a pre-push hook or CI. The template vault's own
  CI is a working example: `.github/workflows/ci.yml` in this repository.
- **No secrets in the vault.** The sync holds back credential-shaped lines and the session logger
  redacts them, but the rule is the real protection: record where a credential lives, never the
  value.
- **Never delete a note.** Move it to `99 - Archive/`; links keep resolving and history stays.

## Lint in CI

```yaml
name: vault
on: [push, pull_request]
permissions:
  contents: read
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install "git+https://github.com/chris-fountoulis/agency-os"
      - run: agency-os lint vault
      - run: agency-os index vault --check
```

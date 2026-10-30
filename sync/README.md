<p align="right"><a href="../README.md">Back to README</a></p>

# sync: keep a shared vault in step with git

Optional. `vault-sync.sh` is one run of: wait until the vault stops changing, commit, pull
teammates' changes, push. Run it every minute in the background and a team of several people
shares one vault through any git remote without thinking about it. For the full team workflow
see [docs/team-setup.md](../docs/team-setup.md).

| File | What it is |
|---|---|
| `vault-sync.sh` | The sync run. Bash and git only |
| `install.sh` | Installs it as a launchd agent (macOS) or a systemd user timer (Linux) |
| `com.agency-os.vault-sync.plist.template` | The launchd agent, every 60 seconds |
| `agency-os-vault-sync.service`, `.timer` | The systemd user units, every 60 seconds |

```bash
sync/install.sh ~/work/acme-vault        # install for one vault repo
sync/install.sh --uninstall              # remove
touch ~/.agency-os-sync-off              # pause every repo
touch ~/work/acme-vault/.git/agency-os-sync-off   # pause one repo
tail -f ~/.agency-os/sync.log            # watch it
```

## What it will not commit

> [!IMPORTANT]
> Held-back files stay in your working tree untracked. Nothing is deleted.

- **Files over 50 MB** (`AGENCY_OS_SYNC_MAX_BYTES`). Git hosts reject large files, and a vault
  is notes, not media.
- **Files whose new lines look like credentials**: provider API keys , GitHub tokens , cloud access
  keys, private key blocks. You get one notification per distinct problem.

## How it resolves changes from teammates

| Situation | What the sync does |
|---|---|
| Behind only | Fast-forward |
| Ahead and behind | Rebase local commits on top of the remote, with autostash |
| Conflict only in generated files (the All Notes Index, or anything matching `AGENCY_OS_SYNC_GENERATED`) | The remote copy wins, the rebase continues and the index is regenerated if `agency-os` is on the PATH |
| A real conflict | The rebase is aborted, nothing is lost and you get one notification to resolve it by hand. Later runs keep committing locally and retry the rebase |

> [!NOTE]
> It never force-pushes, never touches a repo in the middle of a merge or rebase and skips a
> detached HEAD.

---

<p align="right"><a href="../README.md">Back to README</a></p>

<p align="center">Built by <a href="https://chrisfountoulis.com">Chris Fountoulis</a> at <a href="https://growthofinfluence.com">Growth Of Influence</a>.</p>

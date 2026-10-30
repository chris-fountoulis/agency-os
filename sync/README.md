# sync: keep a shared vault in step with git

Optional. `vault-sync.sh` is one run of: wait until the vault stops changing, commit, pull
teammates' changes, push. Run it every minute in the background and a team of several people
shares one vault through any git remote without thinking about it.

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

- **Files over 50 MB** (`AGENCY_OS_SYNC_MAX_BYTES`). Git hosts reject large files, and a vault
  is notes, not media.
- **Files whose new lines look like credentials**: provider API keys, GitHub tokens, cloud access
  keys, private key blocks. The file stays in your working tree, untracked, and you get one
  notification per distinct problem.

## How it resolves changes from teammates

- Behind only: fast-forward.
- Ahead and behind: rebase local commits on top of the remote, with autostash.
- A real conflict: the rebase is aborted, nothing is lost, and you get a notification to
  resolve it by hand. Later runs keep committing locally and retry the rebase; you are
  notified once, not every minute.

It never force-pushes, never touches a repo in the middle of a merge or rebase, and skips a
detached HEAD.

#!/usr/bin/env bash
# Install the vault sync as a background job: launchd on macOS, a systemd user timer on Linux.
# Usage: sync/install.sh /path/to/vault-repo        Remove: sync/install.sh --uninstall
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/vault-sync.sh"
LOG_DIR="$HOME/.agency-os"

escape() { printf '%s' "$1" | sed -e 's/[\/&|]/\\&/g'; }

if [ "${1:-}" = "--uninstall" ]; then
  case "$(uname -s)" in
    Darwin)
      launchctl bootout "gui/$(id -u)/com.agency-os.vault-sync" 2>/dev/null || true
      rm -f "$HOME/Library/LaunchAgents/com.agency-os.vault-sync.plist" ;;
    Linux)
      systemctl --user disable --now agency-os-vault-sync.timer 2>/dev/null || true
      rm -f "$HOME/.config/systemd/user/agency-os-vault-sync."{service,timer}
      systemctl --user daemon-reload ;;
  esac
  echo "vault sync removed"
  exit 0
fi

REPO="${1:?usage: install.sh /path/to/vault-repo}"
REPO="$(cd "$REPO" && pwd)"
git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "not a git repo: $REPO" >&2; exit 1; }
chmod +x "$SCRIPT"
mkdir -p "$LOG_DIR"

case "$(uname -s)" in
  Darwin)
    dest="$HOME/Library/LaunchAgents/com.agency-os.vault-sync.plist"
    mkdir -p "$(dirname "$dest")"
    sed -e "s|__SCRIPT__|$(escape "$SCRIPT")|" -e "s|__REPO__|$(escape "$REPO")|" -e "s|__LOG_DIR__|$(escape "$LOG_DIR")|" \
      "$HERE/com.agency-os.vault-sync.plist.template" > "$dest"
    launchctl bootout "gui/$(id -u)/com.agency-os.vault-sync" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$dest"
    echo "launchd agent installed: $dest" ;;
  Linux)
    dest="$HOME/.config/systemd/user"
    mkdir -p "$dest"
    sed -e "s|__SCRIPT__|$(escape "$SCRIPT")|" -e "s|__REPO__|$(escape "$REPO")|" \
      "$HERE/agency-os-vault-sync.service" > "$dest/agency-os-vault-sync.service"
    cp "$HERE/agency-os-vault-sync.timer" "$dest/"
    systemctl --user daemon-reload
    systemctl --user enable --now agency-os-vault-sync.timer
    echo "systemd timer installed: $dest/agency-os-vault-sync.timer" ;;
  *)
    echo "unsupported OS; run $SCRIPT from your own scheduler" >&2; exit 1 ;;
esac
echo "log: $LOG_DIR/sync.log   pause: touch ~/.agency-os-sync-off"

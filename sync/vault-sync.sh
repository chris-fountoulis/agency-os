#!/usr/bin/env bash
# vault-sync: keep a shared vault in step with its git remote.
#
# One run: wait until files stop changing, commit everything except files that
# are too large or contain credential-shaped lines, pull teammates' changes
# (fast-forward, or rebase local commits on top), then push.
#
# Usage:   vault-sync.sh [REPO_DIR]            (default: $AGENCY_OS_SYNC_REPO or the current folder)
# Pause:   touch ~/.agency-os-sync-off         (every repo)
#          touch REPO_DIR/.git/agency-os-sync-off   (one repo)
# Run it every minute from launchd or a systemd timer: see sync/README.md.
#
# Environment
#   AGENCY_OS_SYNC_MAX_BYTES  hold back files larger than this (default 50000000)
#   AGENCY_OS_SYNC_QUIET      seconds without changes before committing (default 20)
#   AGENCY_OS_SYNC_LOG        log file (default ~/.agency-os/sync.log)
#   AGENCY_OS_SYNC_BRANCH     only sync when this branch is checked out (default: any)
#   AGENCY_OS_SYNC_GENERATED  regex of generated files whose conflicts resolve to the remote copy
#                             (default: All Notes Index.md)

set -u

REPO="${1:-${AGENCY_OS_SYNC_REPO:-$PWD}}"
MAX_BYTES="${AGENCY_OS_SYNC_MAX_BYTES:-50000000}"
QUIET_SECS="${AGENCY_OS_SYNC_QUIET:-20}"
LOG="${AGENCY_OS_SYNC_LOG:-$HOME/.agency-os/sync.log}"
ONLY_BRANCH="${AGENCY_OS_SYNC_BRANCH:-}"
SECRET_RE='(sk-ant-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9_-]{20,}|(sk|rk)_live_[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35})'

mkdir -p "$(dirname "$LOG")"
log() { printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$(basename "$REPO")" "$1" >> "$LOG"; }

notify() {
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$1\" with title \"vault-sync\"" >/dev/null 2>&1
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send "vault-sync" "$1" >/dev/null 2>&1
  fi
}

# Warn once per distinct problem, not once a minute.
warn_once() {
  local key="$GIT_DIR_PATH/agency-os-sync-lastwarn"
  [ "$(cat "$key" 2>/dev/null)" = "$1" ] && return
  printf '%s' "$1" > "$key"
  log "WARN $1"
  notify "$(basename "$REPO"): $1"
}
clear_warn() { rm -f "$GIT_DIR_PATH/agency-os-sync-lastwarn"; }

mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }
size_of() { stat -c %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null || echo 0; }

[ -e "$HOME/.agency-os-sync-off" ] && exit 0
cd "$REPO" 2>/dev/null || { log "repo not found: $REPO"; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { log "not a git repo: $REPO"; exit 1; }
GIT_DIR_PATH="$(git rev-parse --absolute-git-dir)"
[ -e "$GIT_DIR_PATH/agency-os-sync-off" ] && exit 0

# One run at a time per repo; a lock older than 15 minutes is stale.
LOCK="${TMPDIR:-/tmp}/agency-os-sync.$(id -u).$(printf '%s' "$REPO" | cksum | cut -d' ' -f1).lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +15 2>/dev/null)" ]; then
    rm -rf "$LOCK" && mkdir "$LOCK" || exit 0
  else
    exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

BRANCH="$(git symbolic-ref --short -q HEAD)" || exit 0          # detached HEAD: leave it alone
[ -n "$ONLY_BRANCH" ] && [ "$BRANCH" != "$ONLY_BRANCH" ] && exit 0
for state in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD index.lock; do
  [ -e "$GIT_DIR_PATH/$state" ] && exit 0                       # a person is mid-operation
done

held=()
if [ -n "$(git status --porcelain)" ]; then
  # Debounce: Obsidian and Claude Code write in bursts.
  now=$(date +%s); newest=0
  while IFS= read -r -d '' f; do
    [ -f "$f" ] || continue
    m=$(mtime "$f"); [ "$m" -gt "$newest" ] && newest=$m
  done < <(git ls-files -z -m -o --exclude-standard)
  if [ $((now - newest)) -lt "$QUIET_SECS" ]; then
    exit 0
  fi

  git add -A >/dev/null 2>&1
  while IFS= read -r -d '' f; do
    [ -f "$f" ] || continue
    if [ "$(size_of "$f")" -gt "$MAX_BYTES" ] || git diff --cached -U0 -- "$f" | grep '^+' | grep -qE "$SECRET_RE"; then
      git reset -q -- "$f"
      held+=("$f")
    fi
  done < <(git diff --cached --name-only -z --diff-filter=AM)
  if [ ${#held[@]} -gt 0 ]; then
    warn_once "${#held[@]} file(s) held back (credential shape or over size limit): ${held[0]}"
  fi

  if ! git diff --cached --quiet; then
    n=$(git diff --cached --name-only | wc -l | tr -d ' ')
    if git commit -q -m "vault: sync $n file(s) $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1; then
      log "committed $n file(s) on $BRANCH"
    else
      git reset -q
      warn_once "commit refused (a pre-commit hook said no)"
    fi
  fi
fi

git remote get-url origin >/dev/null 2>&1 || exit 0              # local-only vault: commits are enough

if ! git rev-parse --abbrev-ref -q '@{u}' >/dev/null 2>&1; then
  if git push -q -u origin "$BRANCH" >> "$LOG" 2>&1; then
    log "pushed new branch $BRANCH"
  else
    warn_once "first push of $BRANCH failed"
  fi
  exit 0
fi

# A rebase that stops only on generated files (the All Notes Index) is not a real conflict:
# take the remote copy and carry on; the index is regenerated after the rebase.
GENERATED_RE="${AGENCY_OS_SYNC_GENERATED:-All Notes Index\.md\$}"
resolve_generated() {
  local rounds=0 conflicted
  while [ -d "$GIT_DIR_PATH/rebase-merge" ] || [ -d "$GIT_DIR_PATH/rebase-apply" ]; do
    rounds=$((rounds + 1)); [ "$rounds" -gt 50 ] && return 1
    conflicted="$(git diff --name-only --diff-filter=U)"
    [ -n "$conflicted" ] || return 1
    printf '%s\n' "$conflicted" | grep -qvE "$GENERATED_RE" && return 1
    while IFS= read -r f; do
      git checkout -q --ours -- "$f" && git add -- "$f"
    done <<< "$conflicted"
    GIT_EDITOR=true git rebase --continue >> "$LOG" 2>&1 || true
  done
  log "resolved a conflict in generated files by taking the remote copy"
  if command -v agency-os >/dev/null 2>&1; then
    vault_dir="$(dirname "$(git ls-files | grep -E "$GENERATED_RE" | head -1)")/.."
    if agency-os index "$vault_dir" >> "$LOG" 2>&1 && [ -n "$(git status --porcelain)" ]; then
      git add -A && git commit -q -m "vault: regenerate the index after sync" >> "$LOG" 2>&1
    fi
  fi
  return 0
}

git fetch -q origin >> "$LOG" 2>&1 || { warn_once "fetch failed (offline or no access)"; exit 0; }
ahead=$(git rev-list --count '@{u}..HEAD')
behind=$(git rev-list --count 'HEAD..@{u}')

if [ "$behind" -gt 0 ]; then
  if [ "$ahead" -eq 0 ]; then
    if git merge -q --ff-only '@{u}' >> "$LOG" 2>&1; then
      log "pulled $behind commit(s)"
    else
      warn_once "could not fast-forward $BRANCH (uncommitted changes in the way)"
    fi
  elif git rebase -q --autostash '@{u}' >> "$LOG" 2>&1 || resolve_generated; then
    log "rebased $ahead local commit(s) onto $behind remote commit(s)"
  else
    git rebase --abort >/dev/null 2>&1
    warn_once "conflict with the remote on $BRANCH: resolve by hand"
    exit 0
  fi
fi

if [ "$(git rev-list --count '@{u}..HEAD')" -gt 0 ]; then
  if git push -q origin "$BRANCH" >> "$LOG" 2>&1; then
    log "pushed $BRANCH"
    [ ${#held[@]} -eq 0 ] && clear_warn
  else
    warn_once "push failed on $BRANCH"
  fi
fi
exit 0

#!/bin/bash
# Weekly snapshot of live music.db into a private Git LFS clone.
# Paths come from this repo's .env (DB_BACKUP_REPO). Do not hardcode a server layout.
# Cron: 0 3 * * 0 /path/to/spot-seek-bot/backup_db_to_github.sh

set -euo pipefail

export PATH="/usr/bin:/bin:/usr/local/bin:${PATH:-}"
export GIT_TERMINAL_PROMPT=0

SCRIPT_DIR=$(dirname "$(realpath "$0")")
ENV_FILE="${SCRIPT_DIR}/.env"
SRC_DB="${SCRIPT_DIR}/music.db"
LOG="${SCRIPT_DIR}/backup_db_to_github.log"
LOCK="/tmp/spotseek-db-backup.lock"

# Read one KEY=value from python-dotenv .env. Do not `source` the whole file
# (JSON values there are not bash-safe).
env_get() {
    local key="$1"
    local line val
    [ -f "$ENV_FILE" ] || return 0
    line=$(grep -E "^${key}=" "$ENV_FILE" | tail -1) || true
    [ -n "$line" ] || return 0
    val="${line#*=}"
    val="${val%"${val##*[![:space:]]}"}"
    val="${val#\"}"
    val="${val%\"}"
    val="${val#\'}"
    val="${val%\'}"
    printf '%s' "$val"
}

log() {
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*" | tee -a "$LOG"
}

exec 9>"$LOCK"
if ! flock -n 9; then
    log "another backup is already running; skip"
    exit 0
fi

DEST_DIR=$(env_get DB_BACKUP_REPO)

log "backup start"

if [ -z "$DEST_DIR" ]; then
    log "set DB_BACKUP_REPO in .env"
    exit 1
fi
if [ ! -f "$SRC_DB" ]; then
    log "missing source db"
    exit 1
fi
if [ ! -d "${DEST_DIR}/.git" ]; then
    log "missing backup repo (DB_BACKUP_REPO)"
    exit 1
fi

DEST_DB="${DEST_DIR}/music.db"
TMP_DB="${DEST_DIR}/music.db.tmp"
rm -f "$TMP_DB"
# Consistent copy while the bot may still be writing (do not cp the live file).
sqlite3 "$SRC_DB" ".backup '$TMP_DB'"
mv -f "$TMP_DB" "$DEST_DB"

TRACKS=$(sqlite3 "$DEST_DB" "SELECT COUNT(*) FROM track_info;")
DATE_UTC=$(date -u +%Y-%m-%d)
log "snapshot ready (${TRACKS} tracks)"

cd "$DEST_DIR"
git add music.db

if git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
    log "no changes; skip commit"
else
    if ! git diff --cached --quiet; then
        git commit -m "weekly backup ${DATE_UTC} (${TRACKS} tracks)"
        log "committed weekly backup ${DATE_UTC}"
    fi
fi

if [ -n "$(git log --oneline origin/main..HEAD 2>/dev/null)" ] || git status -sb | grep -q 'ahead'; then
    git push origin HEAD
    log "pushed to origin"
else
    log "nothing to push"
fi

log "backup done"

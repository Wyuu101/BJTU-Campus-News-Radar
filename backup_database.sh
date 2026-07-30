#!/usr/bin/env bash
set -euo pipefail

# BJTU Campus News Radar SQLite database backup script.
# Intended for cron. It creates a consistent SQLite backup and removes backups
# outside the retention window.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="${DB_PATH:-${PROJECT_DIR}/data/notice_monitor.sqlite3}"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/data/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-60}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_PATH="${BACKUP_DIR}/notice_monitor_${TIMESTAMP}.sqlite3"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

if [ ! -f "${DB_PATH}" ]; then
  log "Database not found: ${DB_PATH}"
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

export DB_PATH BACKUP_PATH
"${PYTHON_BIN}" - <<'PY'
import os
import sqlite3
from pathlib import Path

source_path = Path(os.environ["DB_PATH"])
backup_path = Path(os.environ["BACKUP_PATH"])
backup_path.parent.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(source_path) as source, sqlite3.connect(backup_path) as backup:
    source.backup(backup)
PY

chmod 600 "${BACKUP_PATH}"
log "Backup created: ${BACKUP_PATH}"

find "${BACKUP_DIR}" \
  -type f \
  -name 'notice_monitor_*.sqlite3' \
  -mtime +"${RETENTION_DAYS}" \
  -print \
  -delete | while IFS= read -r removed_file; do
    log "Removed expired backup: ${removed_file}"
  done

log "Backup finished. Retention window: ${RETENTION_DAYS} days."

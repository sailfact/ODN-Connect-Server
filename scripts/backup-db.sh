#!/usr/bin/env bash
# Backup PostgreSQL to a timestamped gzip file.
# Schedule via cron: 0 3 * * * /path/to/backup-db.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/odn-vpn}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="vpn_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-vpn}" \
  "${POSTGRES_DB:-vpn}" \
  | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "Backup written to ${BACKUP_DIR}/${FILENAME}"

# Prune backups older than 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
echo "Old backups pruned."

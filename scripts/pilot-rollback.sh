#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077

NAME="${1:-}"
if [[ -z "$NAME" || ! "$NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Usage: CONFIRM_ROLLBACK=YES $0 <pre-upgrade-backup-name>" >&2
  exit 2
fi
if [[ "${CONFIRM_ROLLBACK:-NO}" != "YES" ]]; then
  echo "ERROR: rollback is destructive. Set CONFIRM_ROLLBACK=YES after incident/change approval." >&2
  exit 2
fi

MANIFEST="$ROOT/backups/$NAME/backup-manifest.json"
if [[ ! -s "$MANIFEST" ]]; then
  echo "ERROR: backup manifest not found: $MANIFEST" >&2
  exit 3
fi

read_manifest() {
  python - "$MANIFEST" "$1" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
value = payload
for part in sys.argv[2].split("."):
    value = value[part]
if isinstance(value, bool):
    print("true" if value else "false")
else:
    print(value)
PY
}

SCHEMA="$(read_manifest schema)"
BACKUP_SOURCE_COMMIT="$(read_manifest source_commit)"
BACKUP_QUIESCED="$(read_manifest release_consistent_quiesce)"
CURRENT_SOURCE_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo unknown)"

if [[ "$SCHEMA" != "grc-backup-manifest-v1" ]]; then
  echo "ERROR: unsupported backup manifest schema: $SCHEMA" >&2
  exit 3
fi
if [[ "$BACKUP_QUIESCED" != "true" ]]; then
  echo "ERROR: release rollback requires a quiesced pre-upgrade backup." >&2
  exit 3
fi
if [[ "$CURRENT_SOURCE_COMMIT" != "$BACKUP_SOURCE_COMMIT" ]]; then
  echo "ERROR: checkout commit $CURRENT_SOURCE_COMMIT does not match backup source $BACKUP_SOURCE_COMMIT." >&2
  echo "Check out the exact backup source commit before rollback; the script will not change Git state for you." >&2
  exit 4
fi

export CONFIRM_RESTORE=YES
unset RESTORE_ALLOW_FORWARD_COMPATIBLE
exec bash scripts/pilot-restore.sh "$NAME"

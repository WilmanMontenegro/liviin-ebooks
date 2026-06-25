#!/usr/bin/env bash
# Restaura el PDF original desde backup (antes de cualquier edición).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP="$ROOT/fuente/pdf/4_El_arte_de_liderar_tu_hogar_v11_FINAL_backup.pdf"
PDF="$ROOT/fuente/pdf/4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"

if [[ ! -f "$BACKUP" ]]; then
  echo "No hay backup: $BACKUP" >&2
  exit 1
fi

cp -a "$BACKUP" "$PDF"
echo "Restaurado: $PDF ← $BACKUP"
pdfinfo "$PDF" | grep -E 'Pages|File size'

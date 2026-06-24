#!/usr/bin/env bash
# Paquetes Arch/CachyOS — requiere sudo una vez.
set -euo pipefail
echo "Instalando herramientas PDF de sistema..."
sudo pacman -S --needed --noconfirm \
  poppler \
  imagemagick \
  mupdf \
  ghostscript \
  qpdf \
  python-pymupdf \
  2>&1
echo ""
echo "Verificar:"
command -v mutool && mutool -v | head -1
command -v gs && gs --version
command -v qpdf && qpdf --version
echo "Listo. Proyecto: ./pdf setup && ./pdf doctor"

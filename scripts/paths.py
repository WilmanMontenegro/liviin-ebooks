"""Rutas del repo — única fuente de verdad."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WEB = ROOT / "web"
PROMPTS = ROOT / "prompts"

FUENTE_PDF = ROOT / "fuente" / "pdf"
FUENTE_HTML = ROOT / "fuente" / "html"
FUENTE_CSS = ROOT / "fuente" / "css"

ASSETS_PDF = ROOT / "assets" / "pdf"
ASSETS_REF = ROOT / "assets" / "referencia"

ENTREGAS_MESA = ROOT / "entregas" / "mesa"
CLIENTE_AUDIOS = ROOT / "cliente" / "audios"
CLIENTE_TRANSCRIPCIONES = ROOT / "cliente" / "transcripciones"

# PDF fuente (pipeline Liderar / Transformar / Bonus)
LIDERAR_PDF = FUENTE_PDF / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
LIDERAR_BACKUP = FUENTE_PDF / "4_El_arte_de_liderar_tu_hogar_v11_FINAL_backup.pdf"
TRANSFORMAR_PDF = FUENTE_PDF / "El_arte_de_transformar_tu_hogar_v11.pdf"
TRANSFORMAR_BACKUP = FUENTE_PDF / "El_arte_de_transformar_tu_hogar_v11_backup.pdf"
BONUS_PDF = FUENTE_PDF / "Las_manos_que_sostienen_tu_hogar- BONUS 1.pdf"
BONUS_BACKUP = FUENTE_PDF / "Las_manos_que_sostienen_tu_hogar- BONUS 1_backup.pdf"

# Assets usados por scripts PDF
PORTADA_PNG = ASSETS_PDF / "portada ebook 1.png"
QR_PNG = ASSETS_PDF / "HOME EXCEL CODIGO QR.png"
AUTORA_JPG = ASSETS_PDF / "2023-09-11 17.36.28.jpg"

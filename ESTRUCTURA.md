# Estructura del repo

Mapa rápido. Rutas canónicas en `scripts/paths.py`.

```
libro/
├── web/                    # Producto publicado (GitHub Pages)
│   ├── index.html          # Hub ebooks
│   ├── liderar.html …      # Libros en navegador
│   ├── css/                # ebook.css, liviin.css, hub.css
│   ├── assets/             # Portadas web, imágenes piloto
│   ├── pdf/                # PDF descargables (export)
│   └── backups/            # Snippets portada mesa, etc.
│
├── fuente/                 # Material fuente (no entregable directo)
│   ├── pdf/                # PDF edición Liderar, Transformar, Bonus
│   ├── html/               # HTML borrador cliente (mesa, menús…)
│   └── css/                # liviin.css maestro editorial mesa
│
├── entregas/               # PDF que manda la clienta
│   └── mesa/               # Liderar tu mesa + Imprimible asistente
│
├── assets/
│   ├── pdf/                # Portada, QR, foto autora (scripts ./pdf)
│   └── referencia/         # Bocetos, portadas exploratorias, scans
│
├── cliente/
│   ├── audios/             # WhatsApp Ptt
│   └── transcripciones/    # Brief voz → texto
│
├── prompts/                # Prompts IA (portadas, etc.)
├── scripts/                # Builds, auditorías, paths.py
├── pdf                     # CLI ./pdf doctor | cover | html …
└── insert_cover.py         # Shim → scripts/insert_cover.py
```

## Dónde buscar qué

| Busco… | Carpeta |
|--------|---------|
| Ver libro en web | `web/` |
| PDF fuente Liderar | `fuente/pdf/4_El_arte_de_liderar…_FINAL.pdf` |
| PDF mesa cliente | `entregas/mesa/` |
| Portada PNG para `./pdf cover` | `assets/pdf/portada ebook 1.png` |
| HTML original mesa | `fuente/html/LIVIIN_El_arte_de_liderar_tu_mesa.html` |
| Audios MTE | `cliente/audios/` |

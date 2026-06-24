# Lecciones — ebook Liviin (cliente VIP)

## Política

- **Solo lo pedido.** Sin mejoras de diseño no solicitadas.
- Commit git tras cada avance.
- `./pdf doctor` antes y después.

## Producto principal vs PDF fuente (jun 2026 — decisión del cliente)

**Los 3 productos publicados** son los ebooks en `web/`:

| Producto | Ver en web | Descargar |
|----------|------------|-----------|
| El arte de liderar tu hogar | `liderar.html` | `web/pdf/liderar.pdf` |
| El arte de transformar tu hogar | `transformar.html` | `web/pdf/transformar.pdf` |
| Las manos que sostienen tu hogar | `bonus.html` | `web/pdf/bonus.pdf` |

**Los PDF en la raíz del repo** (`4_El_arte_de_liderar…_FINAL.pdf`, `El_arte_de_transformar…`, `Las_manos… BONUS 1.pdf`) son **solo material fuente**: extraer texto, estructura y referencia de diseño. **No son el entregable.**

Pipeline del producto: `./pdf html all` → piloto web → `./pdf export all` (Playwright, WYSIWYG) → `web/pdf/` para el botón Descargar. CI Pages hace html + export en cada push a `main`.

## Error grave a no repetir: las dos rayitas

| Tipo | Aspecto | Acción |
|------|---------|--------|
| **Correcta** | Corta (~45pt), bajo el título, x 46–91 | Conservar → `./pdf underlines` |
| **Incorrecta** | Larga (~339pt), arriba, y≈44 | Borde slot foto → eliminar |

Nunca confundirlas. El usuario lo marcó explícitamente.

## Sin foto en slot

- `./pdf nofoto <págs>` — quita placeholder, sube texto, hueco abajo.
- Ya hecho: 13, 17, 26, 34, 39, 44, 51, 60.

## Entregables clave

- Portada: `portada ebook 1.png`, gap 10pt.
- QR p.89, foto autora p.90.
- Paginación pie derecho: 1–92.
- Índice p.10: 05, 11, 24, 37, 58, 74, 87.

## PDF = no Word

No reflow tipografía. No inventar elementos. Preguntar si hay duda.

## HTML ebooks (GitHub Pages) — sesión jun 2026

**Repo:** `WilmanMontenegro/liviin-ebooks` → https://wilmanmontenegro.github.io/liviin-ebooks/

**Rebuild:** `./pdf html all` (transformar + liderar + `stamp_index` + folios bonus).

**Conteos actuales:** transformar **81** · liderar **91** · bonus **40** páginas (`<div class="page"`).

### Arquitectura

- CSS: `web/css/tokens.css`, `ebook.css`, `hub.css`
- Builds: `scripts/build_transformar_html.py`, `build_liderar_html.py`
- Índice hub: `scripts/stamp_index.py` (tarjetas + fecha + `renumber_ebook_folio` bonus)
- Folios HTML secuenciales en `.banda` (no números PDF); índice interno usa `section_pages` con folio

### Reflow (`build_transformar_html.py`) — reglas clave

| Caso | Función |
|------|---------|
| PDF siguiente liviano | `_is_sparse_continuation` (ymax≤220, ≤14 líneas; citas multi-línea cuentan más) |
| Lista sigue con `•` | `_is_list_continuation` (ymax≤320, ≤20 líneas) — ej. p.83–84 |
| Overview 01–04 | `_is_overview_page` — no `_split_dense_tail` |
| Página densa + liviana | merge siempre si sparse/list; offset Y al fusionar |
| Corte denso p.4 | `_split_dense_tail` solo en hueco de párrafo, nunca mid-frase |
| Citas tras merge | `continues_pull_quote()` en `html_blocks.py` — no partir italic x≥73 |
| Títulos numerados | `.numbered-title` semibold 10px en `ebook.css` |

### Tras cada merge que quita hoja HTML

1. `./pdf html all`
2. Verificar folios sin saltos >3 (`stamp_index` → `verify_band_folio`)
3. Commit + push → Pages CI

### Bugs ya corregidos (no reintroducir)

- ORGANIZAR sin cuerpo: split cortaba en y=415 con overview/merge Y sin offset
- p.56–57 frase partida: preferir merge sparse sobre split
- p.51–52: sparse fallaba por pull-quote multi-línea (umbral líneas)
- p.62 cita partida en dos `<div class="pull-quote">`
- Lista familia p.83–84 en dos hojas

### Pendiente visual

- Revisar otras fusiones tras bajar a 81p
- `01 · ELCAMBIODEVISIÓN` en overview p.8 — posible `collapse_spaced` en labels
- Liderar no tiene reflow merge (solo transformar)

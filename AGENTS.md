# Libro Liviin — guía para agentes

**Cliente importante.** Solo hacer lo que piden. Sin “mejoras” no solicitadas.

Ebook PDF: `fuente/pdf/4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf`
Backup original (no sobrescribir): `fuente/pdf/4_El_arte_de_liderar_tu_hogar_v11_FINAL_backup.pdf`

Mapa completo: `ESTRUCTURA.md` · rutas en `scripts/paths.py`.

## Reglas de oro (leer siempre)

1. **Solo lo pedido** — no añadir líneas, estilos, ni elementos del diseño original “porque queda mejor”.
2. **Distinguir rayitas en PDF:**
   - **Corta bajo el título** (≈45pt, x 46–91) → diseño original → **conservar** al reacomodar (`./pdf underlines`).
   - **Larga arriba** (ancho ~339pt, y≈44) → borde del slot de foto → **borrar**, no es decoración.
3. **Sin foto en slot:** quitar placeholder + **subir texto arriba**, hueco abajo (`./pdf nofoto`). No dejar hueco arriba.
4. **Paginación:** pie derecho = número **secuencial del PDF** (1–92), no 00/01 de capítulo (`./pdf paginate`).
5. **Índice p.10:** números deben coincidir con página real del PDF (`./pdf index`).
6. **Portada:** `COVER_GAP_PT = 10` en `insert_cover.py` — no cambiar sin pedirlo.
7. **Paridad ebooks web:** fix en un libro → mismo fix en Liderar, Transformar y Bonus (salvo que el PDF de ese título no aplique). CSS/bloques comunes primero. Ver `.engram/lessons.md`.

## Modo de trabajo (obligatorio)

1. `./pdf doctor` antes y después de editar.
2. Usar scripts existentes (no reinventar).
3. Verificar visualmente la página tocada.
4. Tras editar **HTML/CSS web** (`web/*.html`, `web/css/`): `./pdf export all` (o `bonus` / `liderar` / …) y commitear `web/pdf/*.pdf` — el botón **Descargar PDF** sirve esos archivos, no el PDF fuente de `fuente/pdf/`.
5. `git commit` por cada avance.
6. `mem_save` en decisiones o errores a no repetir.

No restaurar backup salvo pedido explícito (`./pdf restore`).  
`insert_cover.py` edita el PDF en curso (no parte del backup).

## CLI

```bash
./pdf doctor       # ¿PDF sano?
./pdf html all     # PDF fuente → web/liderar.html + transformar.html
./pdf export all   # web/*.html → web/pdf/*.pdf (Descargar PDF, WYSIWYG)
./pdf export bonus # solo un título
./pdf cover        # portada → assets/pdf/portada ebook 1.png
./pdf qr           # QR p.89
./pdf photo        # foto autora p.90
./pdf paginate     # números 1–92 pie derecho
./pdf index        # corregir índice p.10
./pdf nofoto 13    # quitar slot foto + subir texto
./pdf underlines   # rayita corta bajo título (págs sin foto)
./pdf audit        # placeholders
./pdf restore      # solo si piden deshacer todo
```

## Páginas ya tratadas (sin foto)

13, 17, 26, 34, 39, 44, 51, 60 — texto arriba, sin placeholder, rayita bajo título.

## Assets

| Archivo | Uso |
|---------|-----|
| `assets/pdf/portada ebook 1.png` | Portada p.1 |
| `assets/pdf/HOME EXCEL CODIGO QR.png` | QR p.89 |
| `assets/pdf/ebook 1.png` / `assets/pdf/FOTO MTE 2.jpg` | Foto autora p.90 |

## Índice corregido (p.10)

| Sección | Página PDF |
|---------|------------|
| Iniciación | 05 |
| Filosofía | 11 |
| Conoce tu casa | 24 |
| Equipo | 37 |
| Armonía | 58 |
| Bonus | 74 |
| Cierre | 87 |

## Lo que NO hacer

- No overlays sin redactar placeholders.
- No mover ni inventar líneas decorativas.
- No `git push` sin pedirlo.
- No borrar `*_backup.pdf`.
- No tocar tipografía/fuentes del libro en bloque (PDF no reflow).
- No ser “atrevido” con el diseño — preguntar si hay duda.

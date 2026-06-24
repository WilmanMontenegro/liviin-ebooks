# Libro Liviin — guía para agentes

Ebook PDF: `4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf`  
Backup original (no sobrescribir): `4_El_arte_de_liderar_tu_hogar_v11_FINAL_backup.pdf`

## Modo de trabajo (obligatorio)

1. **Antes de editar:** `./pdf doctor` — confirmar que el PDF abre bien.
2. **Hacer el cambio** con los scripts existentes (no reinventar).
3. **Verificar** visualmente o con `./pdf audit` si aplica.
4. **Git:** commit al terminar cada avance con mensaje claro (qué y por qué).
5. **Engram:** `mem_save` si hubo decisión, bugfix o convención nueva.

No usar `insert_cover.py` restaurando el backup salvo que el usuario pida reset total.  
Los scripts actuales editan el PDF en curso y preservan QR, foto autora y paginación.

## CLI

```bash
./pdf doctor      # ¿PDF sano?
./pdf cover       # portada (portada ebook 1.png)
./pdf qr          # QR p.89
./pdf photo       # foto autora p.90 (ebook 1.png)
./pdf paginate    # números de página 1–92 en pie derecho
./pdf audit       # placeholders por página
./pdf restore     # volver al backup (solo si piden deshacer todo)
```

Entorno: `.venv/bin/python` o `./pdf` (ya apunta al venv).

## Assets

| Archivo | Uso |
|---------|-----|
| `portada ebook 1.png` | Portada p.1 |
| `HOME EXCEL CODIGO QR.png` | QR p.89 |
| `ebook 1.png` | Foto autora p.90 (si falta, reponer antes de `./pdf photo`) |

## Commits

- Un commit por avance lógico (portada, QR, paginación, etc.).
- Incluir PDF + scripts tocados.
- Mensaje en español, foco en el **por qué**.

```bash
git add -A
git commit -m "Descripción del avance"
```

## Lo que no hacer

- No editar el PDF “a mano” con overlays sin redactar placeholders.
- No `git push` sin que el usuario lo pida.
- No borrar `*_backup.pdf`.

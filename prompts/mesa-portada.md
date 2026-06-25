# Portada · El arte de liderar tu mesa

Brief cliente (audios 24 jun 2026):
- **No** foto de MTE, **no** ella cocinando
- **Sí:** mercado/compras **o** plato servido, cena rica
- Para este libro elegimos **cena casera organizada** (liderar la mesa, menús)
- Imprimible aparte → **sin imágenes**

## Regla de oro

Imagen = solo fotografía. Texto y degradado = **HTML/CSS** (`.foto-portada--mesa::after`).

## Versión activa (v4)

- **Estructura:** igual Liderar/Bonus (`foto-portada` + `portada-content`)
- **Asset:** `web/assets/mesa-portada.jpg` (576×520)
- **Fade:** gradiente CSS al fondo `#DFE0DB`, no quemado en el JPG

## Rollbacks

| Versión | HTML | Imagen |
|---------|------|--------|
| Premium mercado | `web/backups/mesa-portada-premium.html` | `mesa-portada-premium.jpg` |
| Hero centrado (feo) | `web/backups/mesa-portada-hero.html` | `mesa-portada-hero-prev.jpg` |

## Prompt portada (cena, sin texto)

```
Photorealistic home dinner, Latin American wholesome meal on wood table: protein, vegetables, salad, rice, sage green napkin. Soft natural light, Liviin muted palette. ZERO text, ZERO people. Full-bleed photo. Fade only in CSS.
```

## Prompt alternativa (mercado)

```
Fresh market groceries on counter: basket, avocados, tomatoes, herbs, eggs. Same rules: no text, no people, full-bleed.
```

# Naturalist specimens (shared)

Fine-line, single-stroke domain illustrations for the Pipelet "Naturalist"
theme — used as curated "specimen" objects (à la a natural-history plate).

`specimen-sprite.svg` defines one `<symbol>` per motif (uniform viewBox
`0 0 100 100`), stroked with `currentColor` and one muted wash each, so the
host theme colours them.

Symbols: `spec-wallbox` `spec-hpc` `spec-connector-type2` `spec-pv`
`spec-battery` `spec-meter` `spec-grid` `spec-house` `spec-leaf`.

Use (after `sync-to-app.sh` rsyncs this into `<app>/static/shared-ui/specimen/`):

```html
<svg class="specimen"><use href="/static/shared-ui/specimen/specimen-sprite.svg#spec-pv"></use></svg>
```
```css
.specimen { width: 64px; height: 64px; color: var(--specimen-stroke, #6A5A43); }
```

Composition + `.specimen` / `.specimen-plate` rules live in the consuming app's
naturalist theme (e.g. `ocpp-edge-dashboard/.../naturalist-theme.css`). The
edge-dashboard container currently serves its own copy from
`html/static/edge/specimen-sprite.svg`; keep the two in sync (this is canonical).

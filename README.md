# pipelet-shared-ui

Shared UI components used across all Pipelet portals.

## What's here

```
pipelet-shared-ui/
├── app-switcher/          Microsoft-Cloud-style 3×3 app switcher
│   ├── apps.json          Source of truth for tile list
│   ├── app-switcher.html  Jinja2 include — renders the trigger + panel
│   ├── app-switcher.css   Prefixed .pipelet-switcher-* styles
│   ├── app-switcher.js    Vanilla ES5, no dependencies
│   ├── flask_helper.py    Drop-in Flask registration helper
│   └── icons/             Momentum lightBronzeWebex icons (self-hosted)
└── deploy/
    └── sync-to-app.sh     Server-side rsync into each app's static dir
```

Philosophy: **no CDN, no npm, no build step**. Everything is plain HTML/CSS/JS
that can be served from each app's `/static/shared-ui/` directory. Intranet-safe.

## Wiring a Flask app

1. Make sure the app's deploy pipeline rsyncs `pipelet-shared-ui/app-switcher/`
   into `{app_static}/shared-ui/app-switcher/` (see `deploy/sync-to-app.sh`).

2. Install the helper module into the app's venv (editable install, or copy):
   ```bash
   pip install -e /opt/pipelet-apps-src/pipelet-shared-ui/app-switcher
   ```

3. Register in the Flask app:
   ```python
   from flask_helper import register_app_switcher  # or symlinked copy
   register_app_switcher(app)
   ```

4. Include in the top-bar of any template:
   ```html
   <header class="topbar">
       {% include "shared-ui/app-switcher/app-switcher.html" %}
       <a href="/" class="topbar-brand">…</a>
       <nav>…</nav>
   </header>
   ```

5. Pull in the CSS/JS once in the page head/foot:
   ```html
   <link rel="stylesheet" href="/static/shared-ui/app-switcher/app-switcher.css">
   <script src="/static/shared-ui/app-switcher/app-switcher.js"></script>
   ```

## Tile definitions

Edit `app-switcher/apps.json` to add/change/activate tiles. Fields:

| Field  | Purpose |
|--------|---------|
| `id`     | Stable identifier, used in CSS `[data-app-id]` |
| `label`  | User-visible name (keep ≤ 2 lines) |
| `url`    | Full https URL; `null` for disabled tiles |
| `icon`   | Icon slug; must match `icons/<slug>.svg` |
| `active` | `true` = clickable, `false` = grayed out |
| `hosts`  | List of host names that should highlight this tile as the "current app" |

Changes deploy on the next `pipelet-deploy` run of any app — no per-app rebuild.

## Versioning

Bump `VERSION` when making breaking changes. The file is read by the deploy
script and by the `register_app_switcher()` helper so migrations can be tracked.

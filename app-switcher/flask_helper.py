"""Flask helper for the Pipelet App-Switcher.

Usage in a Flask app:

    from pipelet_switcher import register_app_switcher
    register_app_switcher(app)

After that, every template rendered by the app has `pipelet_apps` and
`pipelet_current_host` available, so the shared include just works:

    {% include "shared-ui/app-switcher/app-switcher.html" %}

For apps mounted under a URL prefix (e.g. nginx proxies
driver.pipelet.com/driver/* to a Flask on port 9500 which still sees
paths without the /driver prefix), pass `url_prefix=/driver/static`
so the static asset URLs in the HTML come out right.

Behaviour:
- Reads apps.json from the same static directory at import time
  (fast, cached for the process lifetime).
- Adds the apps.json directory as an extra Jinja2 search path so
  {% include %} finds the shared HTML file.
- Injects `pipelet_current_host` from the request's Host header.
- Injects `pipelet_switcher_asset_url` which templates must use for
  all icon / CSS / JS references.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, request


_DEFAULT_STATIC_URL = "/static/shared-ui/app-switcher"


def _default_switcher_dir() -> Path:
    # /opt/pipelet-apps/<app>/static/shared-ui/app-switcher/
    # In dev the path is mirrored under the app repo's static dir.
    here = Path(__file__).resolve().parent
    return here


def register_app_switcher(
    app: Flask,
    switcher_dir: Path | None = None,
    template_subdir: str = "shared-ui/app-switcher",
    static_url: str = _DEFAULT_STATIC_URL,
) -> None:
    """Register the App-Switcher with a Flask app.

    Args:
        app: the Flask app
        switcher_dir: override the on-disk location of app-switcher/
            (default: same dir as this file)
        template_subdir: logical template path the app's include references
        static_url: URL prefix the browser uses to fetch shared-ui assets.
            Default is `/static/shared-ui/app-switcher`. For an app mounted
            under a URL prefix (e.g. /driver/), pass
            `/driver/static/shared-ui/app-switcher` so the CSS/icon URLs
            emitted by the shared template resolve correctly.
    """
    base = switcher_dir or _default_switcher_dir()

    # 1. Load apps.json once
    try:
        with (base / "apps.json").open("r", encoding="utf-8") as f:
            apps_cfg = json.load(f)
        apps = apps_cfg.get("apps", [])
        version = apps_cfg.get("version", "")
    except (FileNotFoundError, json.JSONDecodeError):
        apps = []
        version = ""

    # 2. Make the shared-ui templates reachable as `shared-ui/...`.
    # PrefixLoader ensures the include path matches exactly what the
    # README documents, regardless of the on-disk directory name
    # (which differs between dev symlink and prod rsync).
    from jinja2 import ChoiceLoader, FileSystemLoader, PrefixLoader

    shared_ui_loader = PrefixLoader({
        "shared-ui": FileSystemLoader(str(base.parent)),
    })
    if app.jinja_loader is None:
        app.jinja_loader = shared_ui_loader
    else:
        app.jinja_loader = ChoiceLoader([app.jinja_loader, shared_ui_loader])

    # Normalize the static URL (no trailing slash)
    static_url = static_url.rstrip("/")

    # 3. Context processor — inject apps + current host + URL prefix
    @app.context_processor
    def _inject_pipelet_switcher():
        host = ""
        try:
            # request.host includes port; strip for matching against apps.json hosts
            host = (request.host or "").split(":")[0].lower()
        except RuntimeError:
            # Outside request context (e.g. shell) — fine, no host
            pass
        return {
            "pipelet_apps": apps,
            "pipelet_current_host": host,
            "pipelet_switcher_version": version,
            "pipelet_switcher_asset_url": static_url,
        }

"""Flask helper for the Pipelet App-Switcher.

Usage in a Flask app:

    from pipelet_switcher import register_app_switcher
    register_app_switcher(app)

After that, every template rendered by the app has `pipelet_apps` and
`pipelet_current_host` available, so the shared include just works:

    {% include "shared-ui/app-switcher/app-switcher.html" %}

Behaviour:
- Reads apps.json from the same static directory at import time
  (fast, cached for the process lifetime).
- Adds the apps.json directory as an extra Jinja2 search path so
  {% include %} finds the shared HTML file.
- Injects `pipelet_current_host` from the request's Host header.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, request


def _default_switcher_dir() -> Path:
    # /opt/pipelet-apps/<app>/static/shared-ui/app-switcher/
    # In dev the path is mirrored under the app repo's static dir.
    here = Path(__file__).resolve().parent
    return here


def register_app_switcher(
    app: Flask,
    switcher_dir: Path | None = None,
    template_subdir: str = "shared-ui/app-switcher",
) -> None:
    """Register the App-Switcher with a Flask app.

    - switcher_dir: override the on-disk location of app-switcher/
      (default: same dir as this file)
    - template_subdir: logical template path that the app's include
      will reference. Default matches the rsync layout
      `{static}/shared-ui/app-switcher/app-switcher.html` but exposed
      via the template loader.
    """
    base = switcher_dir or _default_switcher_dir()

    # 1. Load apps.json once
    try:
        with (base / "apps.json").open("r", encoding="utf-8") as f:
            apps_cfg = json.load(f)
        apps = apps_cfg.get("apps", [])
    except (FileNotFoundError, json.JSONDecodeError):
        apps = []

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

    # 3. Context processor — inject apps + current host into every template
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
            "pipelet_switcher_version": apps_cfg.get("version", "") if "apps_cfg" in dir() else "",
        }

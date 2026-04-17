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
    current_user_email_fn=None,
    sso_secret: str = "",
    sso_issuer: str = "",
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
        current_user_email_fn: optional ``() -> str | None`` callback that
            returns the currently-authenticated user's email within a
            request context. When provided together with ``sso_secret``,
            each tile's href gets rewritten to a signed ``/auth/sso``
            URL so click-through stays logged in across portals.
        sso_secret: shared HMAC secret (same value on every portal).
            Without it, SSO link-rewriting is silently disabled and tiles
            fall back to their plain ``app.url``.
        sso_issuer: optional portal id of the source (e.g. ``"sim"``),
            stamped into tokens for audit. Purely informational.
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

    # 3. SSO signer (optional — only when both secret + email-fn provided)
    _sso_enabled = bool(sso_secret) and callable(current_user_email_fn)
    _sso_sign = None
    if _sso_enabled:
        try:
            import importlib.util
            _spec = importlib.util.spec_from_file_location(
                "pipelet_sso", str(base / "sso.py")
            )
            _sso_mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_sso_mod)
            _sso_sign = _sso_mod.sign
        except Exception:
            _sso_enabled = False
            _sso_sign = None

    def _build_sso_urls(apps_list):
        """Per-request: for each SSO-capable app, return a signed /auth/sso URL.

        An app participates only if its apps.json entry has ``"sso": true`` —
        tells us the target portal implements the verify endpoint. Apps
        without this flag (static sites, portals without email auth) keep
        their plain ``app.url`` via the template fallback.
        """
        if not _sso_enabled:
            return {}
        try:
            email = current_user_email_fn()
        except Exception:
            email = None
        if not email:
            return {}
        out = {}
        for a in apps_list:
            if not a.get("active") or not a.get("sso"):
                continue
            base_url = a.get("url")
            if not base_url:
                continue
            try:
                tok = _sso_sign(email, a["id"], sso_secret, iss=sso_issuer)
            except Exception:
                continue
            out[a["id"]] = base_url.rstrip("/") + "/auth/sso?t=" + tok
        return out

    # 4. Context processor — inject apps + current host + URL prefix + SSO URLs
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
            "pipelet_apps_sso_urls": _build_sso_urls(apps),
        }

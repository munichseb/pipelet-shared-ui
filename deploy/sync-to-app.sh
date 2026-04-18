#!/bin/bash
# Sync shared-ui assets into a target app's static directory.
# Called from /usr/local/bin/pipelet-deploy during a pipelet-deploy run.
#
# Layout on the server:
#   /opt/pipelet-apps-src/pipelet-shared-ui/   ← git clone, pulled before deploy
#   /opt/pipelet-apps/<app>/static/shared-ui/  ← rsync target (per app)
#
# Usage:  sync-to-app.sh <app-static-root>
#         e.g. sync-to-app.sh /opt/pipelet-apps/ocpp-chargersim/static

set -eu

SRC="${SHARED_UI_SRC:-/opt/pipelet-apps-src/pipelet-shared-ui}"
APP_STATIC="${1:?Usage: sync-to-app.sh <app-static-root>}"

if [ ! -d "$SRC/app-switcher" ]; then
    echo "sync-to-app.sh: shared-ui source not found at $SRC" >&2
    exit 1
fi
if [ ! -d "$APP_STATIC" ]; then
    echo "sync-to-app.sh: target static dir not found: $APP_STATIC" >&2
    exit 1
fi

mkdir -p "$APP_STATIC/shared-ui"
# app-switcher also contains the shared Pipelet header skin/behaviour
# (pipelet-header.css/js) so the existing sync path stays backward compatible.
rsync -a --delete "$SRC/app-switcher" "$APP_STATIC/shared-ui/"
echo "shared-ui synced to $APP_STATIC/shared-ui/"

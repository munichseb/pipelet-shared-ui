#!/usr/bin/env python3
"""Pipelet naming-convention lint — stop NEW identifier drift.

Canonical vocabulary: see the suite glossary (NAMING.md / Outline
"Naming Conventions & Identifier-Glossar"). This linter is a *ratchet*: it
only inspects ADDED lines in a git diff, so it never trips on the existing
~3.3k legacy uses — it only blocks new surface that introduces a deprecated
alias for a concept that already has a canonical name.

What it flags (on added lines only):
  - new DB columns (CREATE TABLE / ADD COLUMN) using a deprecated alias  -> ERROR
  - new route path/query params using a deprecated alias                 -> ERROR
  - new response/dict keys using a deprecated alias                      -> WARNING

Protocol-defined wire fields (chargePointId, idTag, idToken, transactionId,
connectorId, chargeBoxIdentity, chargingStation, OCPI uid/contract_id/...) are
NOT in the deprecated map and are therefore always allowed.

Suppress a single line by adding a trailing comment containing:  naming-lint: ignore

Usage:
  naming_lint.py                 # diff against $NAMING_LINT_BASE or HEAD~1
  naming_lint.py --base <sha>    # diff against an explicit base
  naming_lint.py --all           # informational full-tree scan (never fails CI)
Exit code 1 if any ERROR-level violation is found (0 otherwise / for --all).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

# deprecated alias -> canonical name (concepts that already HAVE a canonical)
DEPRECATED = {
    "station_id": "chargepoint_id",
    "stationid": "chargepoint_id",
    "cp_id": "chargepoint_id",
    "ocpp_station_id": "chargepoint_id",
    "ocpp_chargepoint_id": "chargepoint_id",
    "connector_idx": "connector_id",
}
# warning-only (deeply embedded / higher false-positive risk)
DEPRECATED_WARN = {
    "charger_id": "chargepoint_id (when it is a charge-box string, not an INT FK)",
    "wallbox_id": "chargepoint_id",
    "single_uuid": "rfid_uid",
    "rfid_uuid": "rfid_uid",
    # WS4 evse_id type-split (NAMING.md §3): snake_case evse_id is overloaded
    # (OCPI string vs INT row-PK). Prefer the disambiguated names. Warn-only:
    # the protocol/wire fields evseId/EVSEId lowercase to 'evseid' (no match),
    # and legacy evse_id dict keys are intentionally kept for back-compat.
    "evse_id": "evse_ocpi_id (OCPI string) or evse_row_id (INT row-PK)",
}

CODE_EXT = (".py", ".js", ".ts", ".jsx", ".tsx")
SQL_EXT = (".sql",)
EXCLUDE = ("/node_modules/", "/venv/", "/.venv/", "/dist/", "/build/",
           "/__pycache__/", "/static/custom/", "/static/vendor/", ".min.js",
           "naming_lint.py")  # the linter must not scan its own deprecated-map

_COL_DEF = re.compile(
    r"\b(?:ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?)?"
    r'"?([a-zA-Z_][a-zA-Z0-9_]*)"?\s+'
    r"(?:VARCHAR|CHAR|TEXT|INT|INTEGER|BIGINT|SMALLINT|SERIAL|BIGSERIAL|"
    r"BOOLEAN|BOOL|TIMESTAMP|TIMESTAMPTZ|DATE|TIME|NUMERIC|DECIMAL|REAL|"
    r"DOUBLE|FLOAT|UUID|JSONB|JSON|BYTEA|INET)\b",
    re.IGNORECASE,
)
_ROUTE_PARAM = re.compile(r"[{<:]\s*(?:int:|str:|string:)?([a-zA-Z_][a-zA-Z0-9_]*)\s*[}>]?")
_DICT_KEY = re.compile(r"""['"]([a-zA-Z_][a-zA-Z0-9_]*)['"]\s*:""")
_MATCHINFO = re.compile(r"""(?:match_info|args|query|view_args|params)(?:\.get)?\s*[\(\[]\s*['"]([a-zA-Z_][a-zA-Z0-9_]*)['"]""")


def _added_lines(base: str):
    """Yield (path, lineno, text) for added lines in the diff vs base."""
    try:
        out = subprocess.run(
            ["git", "diff", "--unified=0", "--no-color", base, "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        print(f"naming-lint: git diff failed ({e}); skipping", file=sys.stderr)
        return
    path, ln = None, 0
    for line in out.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            path = p[2:] if p.startswith("b/") else (None if p == "/dev/null" else p)
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            ln = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            if path:
                yield path, ln, line[1:]
            ln += 1


def _all_lines():
    """Full-tree scan (informational)."""
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout
    for path in out.splitlines():
        if any(x in "/" + path for x in EXCLUDE):
            continue
        if not path.endswith(CODE_EXT + SQL_EXT):
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for i, t in enumerate(f, 1):
                    yield path, i, t.rstrip("\n")
        except OSError:
            continue


def _check(lines):
    errors, warnings = [], []
    for path, ln, text in lines:
        if any(x in "/" + path for x in EXCLUDE):
            continue
        if "naming-lint: ignore" in text:
            continue
        low = path.lower()
        names = set()
        kind = ""
        if low.endswith(SQL_EXT):
            names = {m.lower() for m in _COL_DEF.findall(text)}
            kind = "DB column"
        elif low.endswith(CODE_EXT):
            names = {m.lower() for m in _ROUTE_PARAM.findall(text)}
            names |= {m.lower() for m in _MATCHINFO.findall(text)}
            kind = "route/param"
            # dict keys are warning-only
            for k in _DICT_KEY.findall(text):
                kl = k.lower()
                if kl in DEPRECATED:
                    warnings.append((path, ln, f"response/dict key '{k}' -> use '{DEPRECATED[kl]}'"))
        else:
            continue
        for n in names:
            if n in DEPRECATED:
                errors.append((path, ln, f"new {kind} '{n}' -> use '{DEPRECATED[n]}'"))
            elif n in DEPRECATED_WARN:
                warnings.append((path, ln, f"{kind} '{n}' -> prefer '{DEPRECATED_WARN[n]}'"))
    return errors, warnings


def main() -> int:
    args = sys.argv[1:]
    full = "--all" in args
    base = None
    if "--base" in args:
        base = args[args.index("--base") + 1]
    if not base:
        base = os.environ.get("NAMING_LINT_BASE") or os.environ.get("GITHUB_EVENT_BEFORE")
    if not base or set(base) == {"0"}:
        base = "HEAD~1"

    lines = _all_lines() if full else _added_lines(base)
    errors, warnings = _check(lines)

    for path, ln, msg in warnings:
        print(f"::warning file={path},line={ln}::naming: {msg}")
    for path, ln, msg in errors:
        print(f"::error file={path},line={ln}::naming: {msg}")

    if errors and not full:
        print(f"\nnaming-lint: {len(errors)} error(s), {len(warnings)} warning(s). "
              f"See NAMING.md for the canonical vocabulary. "
              f"Suppress an intentional exception with a 'naming-lint: ignore' comment.")
        return 1
    print(f"naming-lint: OK ({len(warnings)} warning(s)" +
          (", informational --all scan" if full else "") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())

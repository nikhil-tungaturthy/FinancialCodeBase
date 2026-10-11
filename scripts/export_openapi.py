#!/usr/bin/env python3
"""Export the Meridian Flow OpenAPI document to ``shared/contracts/openapi.json``.

Usage (from the repository root):

    uv run python scripts/export_openapi.py            # write or refresh the contract file
    uv run python scripts/export_openapi.py --check    # exit 1 when the committed file is stale
    uv run python scripts/export_openapi.py -o build/openapi.json

The document is produced by ``app.main.create_app().openapi()`` and serialised with sorted
keys, two-space indentation and a trailing newline so that diffs stay stable across runs.
``make contracts`` runs this script and then regenerates the TypeScript client types.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "services" / "api"
DEFAULT_OUTPUT = REPO_ROOT / "shared" / "contracts" / "openapi.json"


def load_document() -> dict[str, Any]:
    """Build the FastAPI application and return its OpenAPI document."""
    if str(API_DIR) not in sys.path:
        sys.path.insert(0, str(API_DIR))
    try:
        from app.main import create_app
    except ImportError as exc:  # pragma: no cover - environment problem, not a code path to test
        raise SystemExit(
            "error: cannot import app.main:create_app "
            f"({exc}). Run this script with 'uv run' from the repository root after 'make setup'."
        ) from exc
    application = create_app()
    document: dict[str, Any] = application.openapi()
    return document


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def describe(document: dict[str, Any]) -> str:
    paths = len(document.get("paths", {}))
    schemas = len(document.get("components", {}).get("schemas", {}))
    version = document.get("info", {}).get("version", "?")
    return f"{paths} paths, {schemas} schemas, api version {version}"


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"destination file (default: {relative(DEFAULT_OUTPUT)})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if the destination differs from the generated document",
    )
    args = parser.parse_args(argv)

    output = Path(args.output).resolve()
    document = load_document()
    rendered = render(document)

    if args.check:
        if not output.exists():
            print(
                f"contract check failed: {relative(output)} does not exist (run 'make contracts')"
            )
            return 1
        if output.read_text(encoding="utf-8") != rendered:
            print(
                f"contract check failed: {relative(output)} is out of date (run 'make contracts')"
            )
            return 1
        print(f"contract up to date: {relative(output)} ({describe(document)})")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    unchanged = output.exists() and output.read_text(encoding="utf-8") == rendered
    output.write_text(rendered, encoding="utf-8")
    state = "unchanged" if unchanged else "updated"
    print(f"wrote {relative(output)} ({describe(document)}; {state})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Generate OpenAPI JSON documentation from the FastAPI application.

Usage:
    python scripts/generate_api_docs.py                    # stdout
    python scripts/generate_api_docs.py -o docs/openapi.json   # write to file

The script introspects the running FastAPI app object and serializes its
OpenAPI schema to JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure backend package is importable
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))


def generate() -> dict:
    """Import the FastAPI app and return its OpenAPI schema dict."""
    from app.main import app  # noqa: E402

    schema = app.openapi()
    return schema


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpenAPI JSON for RealDeal AI")
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent level (default: 2)",
    )
    args = parser.parse_args()

    schema = generate()
    json_str = json.dumps(schema, indent=args.indent, ensure_ascii=False)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_str + "\n", encoding="utf-8")
        print(f"[+] OpenAPI spec written to {out_path} ({len(schema.get('paths', {}))} endpoints)")
    else:
        print(json_str)


if __name__ == "__main__":
    main()

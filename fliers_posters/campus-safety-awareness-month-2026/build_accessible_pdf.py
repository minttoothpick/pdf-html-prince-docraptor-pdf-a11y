#!/usr/bin/env python3
"""Build the OTC Campus Safety poster as a tagged PDF/UA-1 document.

The maintained source is poster-v2.template.html plus build.mjs and assets/.
By default this script rebuilds the self-contained HTML, then sends it to
DocRaptor's Prince pipeline in watermarked test mode. Use --production with a
real DOCRAPTOR_API_KEY to create the unwatermarked website deliverable.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BUILT_HTML = PROJECT_ROOT / "output" / "otc-campus-safety-awareness-poster.html"
TEST_PDF = (
    PROJECT_ROOT
    / "output"
    / "pdf"
    / "otc-campus-safety-awareness-poster-preview.pdf"
)
PRODUCTION_PDF = (
    PROJECT_ROOT
    / "output"
    / "pdf"
    / "otc-campus-safety-awareness-poster-accessible.pdf"
)
PUBLIC_TEST_KEY = "YOUR_API_KEY_HERE"
API_URL = "https://api.docraptor.com/docs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the tagged OTC Campus Safety poster with DocRaptor."
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Create an unwatermarked PDF using DOCRAPTOR_API_KEY.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help=(
            "Use an existing self-contained HTML file instead of running build.mjs. "
            "Relative paths are resolved from this script's directory."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional PDF output path, resolved from this script's directory.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=240,
        help="DocRaptor request timeout in seconds (default: 240).",
    )
    return parser.parse_args()


def resolve_from_project(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def html_source(input_path: Path | None) -> tuple[Path, str]:
    if input_path is None:
        try:
            subprocess.run(
                ["node", "build.mjs"],
                cwd=PROJECT_ROOT,
                check=True,
            )
        except FileNotFoundError as error:
            raise SystemExit("Node.js is required to run build.mjs.") from error
        except subprocess.CalledProcessError as error:
            raise SystemExit(f"The HTML build failed with exit code {error.returncode}.") from error
        path = BUILT_HTML
    else:
        path = resolve_from_project(input_path)

    if not path.is_file():
        raise SystemExit(f"HTML input not found: {path}")

    html = path.read_text(encoding="utf-8")
    required_markers = (
        '<html lang="en">',
        "<title>OTC National Campus Safety Awareness Month</title>",
        "<main",
        "<h1",
    )
    missing = [marker for marker in required_markers if marker not in html]
    if missing:
        raise SystemExit(
            "HTML accessibility preflight failed; missing: " + ", ".join(missing)
        )
    return path, html


def output_path(args: argparse.Namespace) -> Path:
    selected = args.output or (PRODUCTION_PDF if args.production else TEST_PDF)
    return resolve_from_project(selected)


def api_key(production: bool) -> str:
    configured = os.environ.get("DOCRAPTOR_API_KEY", "").strip()
    if production and (not configured or configured == PUBLIC_TEST_KEY):
        raise SystemExit(
            "Production generation requires a real DOCRAPTOR_API_KEY environment variable."
        )
    return configured or PUBLIC_TEST_KEY


def docraptor_request(*, html: str, production: bool, timeout: int) -> tuple[bytes, str | None]:
    payload = {
        "type": "pdf",
        "test": not production,
        "name": "OTC Campus Safety Awareness Month",
        "pipeline": "10.1",
        "document_content": html,
        "prince_options": {
            "profile": "PDF/UA-1",
            "media": "print",
            "no_network": True,
        },
    }
    credentials = base64.b64encode(
        f"{api_key(production)}:".encode("utf-8")
    ).decode("ascii")
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "User-Agent": "OTC-Campus-Safety-PDF/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get("X-DocRaptor-Num-Pages")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"DocRaptor returned HTTP {error.code}:\n{detail}") from error
    except urllib.error.URLError as error:
        raise SystemExit(f"Could not connect to DocRaptor: {error}") from error


def main() -> int:
    args = parse_args()
    source_path, html = html_source(args.input)
    destination = output_path(args)

    mode = "production" if args.production else "watermarked test"
    print(f"Input:  {source_path}")
    print(f"Mode:   {mode}")
    print("Profile: PDF/UA-1 (DocRaptor pipeline 10.1 / Prince 15.1)")
    print("Sending self-contained HTML to DocRaptor...")

    pdf_bytes, page_count = docraptor_request(
        html=html,
        production=args.production,
        timeout=args.timeout,
    )
    if not pdf_bytes.startswith(b"%PDF-"):
        raise SystemExit("DocRaptor returned data that does not appear to be a PDF.")
    if page_count and page_count != "1":
        raise SystemExit(
            f"DocRaptor generated {page_count} pages; expected exactly 1. "
            "The PDF was not saved."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf_bytes)
    print(f"Created: {destination}")
    if page_count:
        print(f"Pages:   {page_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

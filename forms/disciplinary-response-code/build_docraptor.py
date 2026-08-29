#!/usr/bin/env python3

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# PATHS
# ============================================================

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

HTML_FILE = HERE / "drc.html"
CSS_FILE = HERE / "drc.css"
ASSETS_DIR = HERE / "assets"

TEST_OUTPUT_DIR = HERE / "pdf_test"
PRODUCTION_OUTPUT_DIR = HERE / "pdf_production"


# ============================================================
# COMMAND-LINE OPTIONS
# ============================================================

parser = argparse.ArgumentParser(
    description="Build the OTC Disciplinary Response Code with DocRaptor."
)

parser.add_argument(
    "--production",
    action="store_true",
    help=(
        "Create a production DocRaptor document. "
        "This counts against the monthly document allowance."
    ),
)

args = parser.parse_args()
test_mode = not args.production


# ============================================================
# ENVIRONMENT / API KEY
# ============================================================

load_dotenv(REPO_ROOT / ".env")

api_key = os.environ.get("DOCRAPTOR_API_KEY")

if not api_key:
    sys.exit(
        "\nDOCRAPTOR_API_KEY is not set.\n\n"
        "Add it to the repo-level .env file:\n\n"
        "  DOCRAPTOR_API_KEY=your_api_key_here\n"
    )


# ============================================================
# CHECK AND LOAD SOURCE FILES
# ============================================================

for path in (HTML_FILE, CSS_FILE, ASSETS_DIR):
    if not path.exists():
        sys.exit(f"Required path not found: {path}")

html = HTML_FILE.read_text(encoding="utf-8")
css = CSS_FILE.read_text(encoding="utf-8")


# ============================================================
# EMBED CSS
# ============================================================

stylesheet_pattern = re.compile(
    r'<link\b'
    r'(?=[^>]*\brel=["\']stylesheet["\'])'
    r'(?=[^>]*\bhref=["\']drc\.css["\'])'
    r'[^>]*>',
    flags=re.IGNORECASE,
)

html, css_replacements = stylesheet_pattern.subn(
    "<style>\n" + css + "\n</style>",
    html,
    count=1,
)

if css_replacements != 1:
    sys.exit("Could not find the drc.css <link> element in drc.html.")


# ============================================================
# EMBED LOCAL IMAGES
# ============================================================

asset_references = set(
    re.findall(r'src=["\']assets/([^"\']+)["\']', html, flags=re.IGNORECASE)
)

for asset_name in sorted(asset_references):
    asset_path = ASSETS_DIR / asset_name

    if not asset_path.is_file():
        sys.exit(f"Required asset not found: {asset_path}")

    mime_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    data_uri = f"data:{mime_type};base64,{encoded}"

    html = html.replace(f'src="assets/{asset_name}"', f'src="{data_uri}"')
    html = html.replace(f"src='assets/{asset_name}'", f'src="{data_uri}"')

if re.search(r'src=["\']assets/', html, flags=re.IGNORECASE):
    sys.exit("One or more local image references could not be embedded.")


# ============================================================
# OUTPUT FILE
# ============================================================

if test_mode:
    output_dir = TEST_OUTPUT_DIR
    output_file = output_dir / "disciplinary-response-code-test.pdf"
    mode_label = "TEST"
else:
    output_dir = PRODUCTION_OUTPUT_DIR
    output_file = output_dir / "disciplinary-response-code-2026-2027.pdf"
    mode_label = "PRODUCTION"

output_dir.mkdir(parents=True, exist_ok=True)


# ============================================================
# DOCRAPTOR REQUEST
# ============================================================

payload = {
    "type": "pdf",
    "test": test_mode,
    "name": "Orange Technical College - 2026-2027 Disciplinary Response Code",
    "pipeline": "10.1",
    "document_content": html,
    "prince_options": {
        "profile": "PDF/UA-1",
        "media": "print",
        "no_subset_fonts": True,
    },
}

credentials = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")

request = urllib.request.Request(
    "https://api.docraptor.com/docs",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {credentials}",
        "User-Agent": "OTC-PDF-Remediation/1.0",
    },
    method="POST",
)


# ============================================================
# BUILD
# ============================================================

print()
print("Document: OTC Disciplinary Response Code 2026-2027")
print(f"Mode:     {mode_label}")
print()
print("Sending document to DocRaptor...")

try:
    with urllib.request.urlopen(request, timeout=180) as response:
        pdf_bytes = response.read()
        page_count = response.headers.get("X-DocRaptor-Num-Pages")

except urllib.error.HTTPError as error:
    body = error.read().decode("utf-8", errors="replace")
    print()
    print(f"DocRaptor returned HTTP {error.code}:")
    print()
    print(body)
    print()
    sys.exit(1)

except urllib.error.URLError as error:
    sys.exit(f"\nCould not connect to DocRaptor:\n{error}\n")

except Exception as error:
    sys.exit(f"\nDocRaptor request failed:\n{error}\n")


# ============================================================
# VERIFY AND SAVE
# ============================================================

if not pdf_bytes.startswith(b"%PDF-"):
    sys.exit("\nDocRaptor returned data that does not appear to be a PDF.\n")

output_file.write_bytes(pdf_bytes)

print()
print(f"Created: {output_file}")

if page_count:
    print(f"Pages:   {page_count}")

if test_mode:
    print("Mode:    TEST - does not use a production credit.")
else:
    print("Mode:    PRODUCTION - uses one production credit.")

print()

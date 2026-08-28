#!/usr/bin/env python3

import argparse
import base64
import json
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

HTML_FILE = HERE / "model-release-form.html"
CSS_FILE = HERE / "model-release-form.css"
LOGO_FILE = REPO_ROOT / "assets" / "otc-career-logo.png"

TEST_OUTPUT_DIR = HERE / "pdf_test"
PRODUCTION_OUTPUT_DIR = HERE / "pdf_production"


# ============================================================
# COMMAND-LINE OPTIONS
# ============================================================

parser = argparse.ArgumentParser(
    description="Build the OTC Model Release Form with DocRaptor."
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
# CHECK SOURCE FILES
# ============================================================

for path in (HTML_FILE, CSS_FILE, LOGO_FILE):
    if not path.exists():
        sys.exit(f"Required file not found: {path}")


# ============================================================
# LOAD SOURCE
# ============================================================

html = HTML_FILE.read_text(encoding="utf-8")
css = CSS_FILE.read_text(encoding="utf-8")


# ============================================================
# EMBED CSS
# ============================================================

stylesheet_pattern = re.compile(
    r'<link\b'
    r'(?=[^>]*\brel=["\']stylesheet["\'])'
    r'(?=[^>]*\bhref=["\']model-release-form\.css["\'])'
    r'[^>]*>',
    flags=re.IGNORECASE,
)

html, css_replacements = stylesheet_pattern.subn(
    "<style>\n" + css + "\n</style>",
    html,
    count=1,
)

if css_replacements != 1:
    sys.exit(
        "Could not find the model-release-form.css <link> element "
        "in model-release-form.html."
    )


# ============================================================
# EMBED LOGO
# ============================================================

logo_bytes = LOGO_FILE.read_bytes()
logo_base64 = base64.b64encode(logo_bytes).decode("ascii")
logo_uri = f"data:image/png;base64,{logo_base64}"

html, logo_replacements = re.subn(
    r'src=["\']\.\./\.\./assets/otc-career-logo\.png["\']',
    f'src="{logo_uri}"',
    html,
    count=1,
    flags=re.IGNORECASE,
)

if logo_replacements != 1:
    sys.exit(
        "Could not find ../../assets/otc-career-logo.png "
        "in model-release-form.html."
    )


# ============================================================
# OUTPUT FILE
# ============================================================

if test_mode:
    output_dir = TEST_OUTPUT_DIR
    output_file = output_dir / "model-release-form-test.pdf"
    mode_label = "TEST"
else:
    output_dir = PRODUCTION_OUTPUT_DIR
    output_file = output_dir / "model-release-form.pdf"
    mode_label = "PRODUCTION"

output_dir.mkdir(parents=True, exist_ok=True)


# ============================================================
# DOCRAPTOR REQUEST
# ============================================================

payload = {
    "type": "pdf",
    "test": test_mode,
    "name": "Orange County Public Schools - Model Release Form",
    # Keep using the same pipeline that produced the successful
    # OTC PDF/UA form output.
    "pipeline": "10.1",
    "document_content": html,
    "prince_options": {
        "profile": "PDF/UA-1",
        "media": "print",
        "no_subset_fonts": True,
    },
}


# ============================================================
# AUTHENTICATION
# ============================================================

credentials = base64.b64encode(
    f"{api_key}:".encode("utf-8")
).decode("ascii")

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
print("Form: Model Release Form")
print(f"Mode: {mode_label}")
print()
print("Sending document to DocRaptor...")

try:
    with urllib.request.urlopen(request, timeout=120) as response:
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
    sys.exit(
        f"\nCould not connect to DocRaptor:\n{error}\n"
    )

except Exception as error:
    sys.exit(
        f"\nDocRaptor request failed:\n{error}\n"
    )


# ============================================================
# VERIFY RESPONSE LOOKS LIKE PDF
# ============================================================

if not pdf_bytes.startswith(b"%PDF-"):
    sys.exit(
        "\nDocRaptor returned data that does not appear "
        "to be a PDF.\n"
    )


# ============================================================
# SAVE
# ============================================================

output_file.write_bytes(pdf_bytes)

print()
print(f"Created: {output_file}")

if page_count:
    print(f"Pages:   {page_count}")

if test_mode:
    print("Mode:    TEST — does not use a production credit.")
else:
    print("Mode:    PRODUCTION — uses one production credit.")

print()
